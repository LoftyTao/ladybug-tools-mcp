"""honeybee_core MCP tools."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field


def register(mcp: FastMCP) -> None:
    """Register honeybee_core tools."""

    @mcp.tool(
        name="HB_Apply_Room_Energy_Properties",
        description=(
            'Apply one shared set of Honeybee Energy properties atomically to multiple Room '
            'targets in one Garden Honeybee Model. Provide exactly one of room_targets (typed '
            'targets from HB_Search_Model_Objects) or room_identifiers, plus energy_properties '
            'containing only program_type, construction_set, template hvac, ventilation, '
            'setpoint, or zone_ventilation_fans. The tool resolves and validates every Room and '
            'property reference before one Garden save; any missing Room, cross-model target, '
            'invalid reference, or revision conflict leaves the model unchanged. Returns '
            'updated_room_count, a limited Room identifier sample, model_target, '
            'persistence_receipt, and report. Identical values return no_change without another '
            'model revision.'
        ),
        tags={
            "apply",
            "batch",
            "construction-set",
            "energy",
            "honeybee",
            "hvac-template",
            "program-type",
            "room",
            "setpoint",
            "ventilation",
        },
        timeout=30,
    )
    def apply_room_energy_properties(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']."
                )
            ),
        ],
        energy_properties: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required shared property changes. Supported keys are only "
                    "program_type, construction_set, hvac, ventilation, setpoint, "
                    "and zone_ventilation_fans; values may be SDK dictionaries, "
                    "Garden property targets, or supported standard identifiers."
                )
            ),
        ],
        room_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Optional non-empty list of Honeybee Room typed targets from '
                    'HB_Search_Model_Objects.matches[i].target. Mutually exclusive with '
                    'room_identifiers.'
                )
            ),
        ] = None,
        room_identifiers: Annotated[
            list[str] | None,
            Field(
                description=(
                    'Optional non-empty list of exact Room identifiers in the selected Honeybee '
                    'Model. Mutually exclusive with room_targets.'
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee Model target, usually HB_Create_Model['target']; "
                    "defaults to the Garden base Honeybee Model. Every typed Room "
                    "target must belong to this same model and Garden."
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Apply shared Honeybee Room Energy properties."""
        from garden.honeybee_core.room_energy import (
            apply_room_energy_properties as service,
        )

        return service(
            garden_root=garden_root,
            energy_properties=energy_properties,
            room_targets=room_targets,
            room_identifiers=room_identifiers,
            model_target=model_target,
        )

    @mcp.tool(
        name="HB_Create_Aperture",
        description=(
            'Create a Honeybee Aperture, commonly a window/opening sub-face, on a host Honeybee '
            'Face typed target from explicit Face3D geometry. Use '
            'HB_Create_Apertures_By_Parameters for parametric or ratio-based windows. Requires '
            'garden_root, identifier, geometry, and host_target from HB_Search_Model_Objects '
            'matches[i].target or HB_Create_Face. Returns target, object_target, model_target, '
            'aperture_target, summary_view, persistence_receipt, and report.'
        ),
        tags={
            "aperture",
            "author",
            "geometry",
            "honeybee",
            "window",
        },
        timeout=20,
    )
    def create_honeybee_aperture(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee aperture identifier.")
        ],
        geometry: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ladybug Geometry Face3D dict fully inside the host face; for '
                    "example {'type':'Face3D','boundary':[[x,y,z],...]}. Boundary points may also "
                    "be {'x':0,'y':0,'z':0} Point3D dicts. Keep sub-face edges inset from the "
                    'host face boundary by at least model tolerance, and omit plane unless '
                    'providing Ladybug Plane keys n, o, and x.'
                )
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Honeybee face typed target dict from HB_Search_Model_Objects '
                    'matches[i].target or HB_Create_Face.'
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        is_operable: Annotated[
            bool, Field(description="Whether the aperture is operable.")
        ] = False,
    ) -> dict[str, Any]:
        """Create a Honeybee Aperture."""
        from garden.honeybee_core.creation import create_honeybee_aperture as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            host_target=host_target,
            model_target=model_target,
            is_operable=is_operable,
        )

    @mcp.tool(
        name="HB_Create_Apertures_By_Guide_Surface",
        description=(
            "Create Honeybee Apertures on a host Face typed target from one or "
            "more Ladybug Geometry Face3D guide surfaces. Guide surfaces must "
            "be coplanar with and fully inside the host Face within tolerance; "
            "non-coplanar, outside, overlapping, invalid, and unprojectable "
            "guides are skipped with reasons. Existing equivalent Apertures "
            "are reused without duplication. Requires garden_root, "
            "host_target, and guide_surfaces. Returns target, targets, "
            "created_targets, reused_targets, summary_view, "
            "persistence_receipt, and report."
        ),
        tags={
            "aperture",
            "author",
            "face",
            "geometry",
            "guide-surface",
            "honeybee",
            "window",
        },
        timeout=20,
    )
    def create_honeybee_apertures_by_guide_surface(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']."
                )
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Honeybee Face typed target from "
                    "HB_Search_Model_Objects matches[i].target."
                )
            ),
        ],
        guide_surfaces: Annotated[
            list[dict[str, Any]],
            Field(
                description=(
                    "Required list of Ladybug Geometry Face3D dictionaries used "
                    "as aperture guide surfaces."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target dict; defaults to the Garden "
                    "base Honeybee Model."
                )
            ),
        ] = None,
        tolerance: Annotated[
            float,
            Field(description="Geometry tolerance for coplanarity and containment."),
        ] = 0.01,
        identifier_prefix: Annotated[
            str | None,
            Field(description="Optional prefix for generated aperture identifiers."),
        ] = None,
    ) -> dict[str, Any]:
        """Create Honeybee Apertures from guide surfaces."""
        from garden.honeybee_core.guide_openings import (
            create_honeybee_apertures_by_guide_surface as service,
        )

        return service(
            garden_root=garden_root,
            host_target=host_target,
            guide_surfaces=guide_surfaces,
            model_target=model_target,
            tolerance=tolerance,
            identifier_prefix=identifier_prefix,
        )

    @mcp.tool(
        name="HB_Create_Apertures_By_Parameters",
        description='Create Honeybee Apertures, windows, rectangular windows, glazed openings, glazing ratio, window-to-wall ratio, or WWR openings on a host exterior wall Face typed target by ratio or by width and height. This is the preferred tool for requests like add windows by WWR, set window-to-wall ratio to 0.3, add rectangular windows, or apply glazing percentage; use HB_Create_Aperture only for explicit Face3D geometry. Prefer a face match where face_type is Wall and boundary_condition is Outdoors. If the host already has apertures, it returns existing aperture targets with created_count=0 instead of duplicating windows. Requires garden_root, host_target, and mode-specific parameters. Returns target, aperture_target, targets, summary_view, persistence_receipt, and report.',
        tags={
            "aperture",
            "author",
            "face",
            "geometry",
            "honeybee",
            "window",
            "wwr",
        },
        timeout=20,
    )
    def create_honeybee_apertures_by_parameters(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee face typed target dict from HB_Search_Model_Objects matches[i].target or a prior create result; choose a Wall/Outdoors face for exterior windows."
            ),
        ],
        generation_mode: Annotated[
            str | None,
            Field(
                description="Generation mode: by_ratio or by_width_height. by_ratio requires ratio; by_width_height requires aperture_width and aperture_height."
            ),
        ] = "by_ratio",
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        ratio: Annotated[
            float | None,
            Field(
                description="Required for by_ratio mode: aperture-to-face area ratio between 0 and 1, for example 0.3."
            ),
        ] = None,
        aperture_width: Annotated[
            float | None,
            Field(
                description="Required for by_width_height mode: single aperture width in model units."
            ),
        ] = None,
        aperture_height: Annotated[
            float | None,
            Field(
                description="Required for by_width_height mode: single aperture height in model units."
            ),
        ] = None,
        sill_height: Annotated[
            float,
            Field(description="Sill height for by_width_height mode in model units."),
        ] = 1.0,
        aperture_identifier: Annotated[
            str | None,
            Field(
                description="Optional aperture identifier for by_width_height mode. Defaults to SDK naming."
            ),
        ] = None,
        identifier_prefix: Annotated[
            str | None,
            Field(
                description='Optional prefix for created aperture identifiers.'
            ),
        ] = None,
        tolerance: Annotated[
            float, Field(description="Geometry tolerance used by by_ratio mode.")
        ] = 0.01,
        rect_split: Annotated[
            bool,
            Field(
                description="Whether by_ratio should split apertures into rectangles when needed."
            ),
        ] = True,
    ) -> dict[str, Any]:
        """Create Honeybee Apertures on a host Face by ratio or width/height parameters."""
        from garden.honeybee_core.creation import (
            create_honeybee_apertures_by_parameters as service,
        )

        return service(
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
        )

    @mcp.tool(
        name="HB_Create_Door",
        description=(
            'Create a Honeybee Door on a host Honeybee Face typed target. For an ordinary '
            'rectangular door, omit geometry and pass door_width, door_height, and sill_height; '
            'the service places it inside the host wall and avoids existing apertures or doors '
            'when possible. For a shared interior Surface boundary wall between adjacent rooms, '
            'this creates the paired adjacent Door automatically and preserves Honeybee Surface '
            'adjacency. Pass geometry only for explicit custom Face3D geometry. Returns target, '
            'object_target, model_target, door_target, and for paired interior doors also '
            'targets, adjacent_target, and summary_view.is_interior_pair.'
        ),
        tags={
            "author",
            "door",
            "geometry",
            "honeybee",
            "hosted",
            "surface",
        },
        timeout=20,
    )
    def create_honeybee_door(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee door identifier.")
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Honeybee face typed target dict from HB_Search_Model_Objects '
                    'matches[i].target or HB_Create_Face. Use a Surface boundary wall face to '
                    'create a paired interior door between adjacent rooms.'
                )
            ),
        ],
        geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Required Ladybug Geometry Face3D dict fully inside the host face; for '
                    "example {'type':'Face3D','boundary':[[x,y,z],...]}. Boundary points may also "
                    "be {'x':0,'y':0,'z':0} Point3D dicts. Keep door edges inset from the host "
                    'face boundary by at least model tolerance (for a floor-touching door, use a '
                    'small positive sill such as z=0.01). Omit plane unless providing Ladybug '
                    'Plane keys n, o, and x.'
                )
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        door_width: Annotated[
            float | None,
            Field(
                description="Optional width for an ordinary rectangular door when geometry is omitted. Defaults to 0.9 meters and avoids existing apertures/doors when possible."
            ),
        ] = None,
        door_height: Annotated[
            float,
            Field(
                description="Optional height for an ordinary rectangular door when geometry is omitted. Defaults to 2.1 meters."
            ),
        ] = 2.1,
        sill_height: Annotated[
            float,
            Field(
                description="Optional bottom offset above the host wall base for an ordinary rectangular door when geometry is omitted. A user-style 0.0 floor sill is accepted; the service applies the minimum Honeybee-safe inset needed to keep the generated door inside the parent face."
            ),
        ] = 0.05,
        placement: Annotated[
            str,
            Field(
                description="Optional placement preference for generated rectangular doors: auto, left, right, or center. auto chooses the first free span that does not overlap existing apertures or doors."
            ),
        ] = "auto",
        is_glass: Annotated[
            bool, Field(description="Whether the door is glass.")
        ] = False,
    ) -> dict[str, Any]:
        """Create a Honeybee Door."""
        from garden.honeybee_core.creation import create_honeybee_door as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            host_target=host_target,
            model_target=model_target,
            is_glass=is_glass,
            door_width=door_width,
            door_height=door_height,
            sill_height=sill_height,
            placement=placement,
        )

    @mcp.tool(
        name="HB_Create_Face",
        description=(
            'Create an orphaned Honeybee Face from a Ladybug Geometry Face3D dictionary and '
            'persist it in the Garden Honeybee Model. The Honeybee SDK infers default face type '
            'and boundary condition. Requires garden_root, identifier, and geometry. Downstream '
            'tools use the returned nested target dict. Returns target, object_target, '
            'model_target, face_target, summary_view, persistence_receipt, and report.'
        ),
        tags={
            "author",
            "face",
            "geometry",
            "honeybee",
        },
        timeout=20,
    )
    def create_honeybee_face(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee face identifier.")
        ],
        geometry: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ladybug Geometry Face3D dict, for example '
                    "{'type':'Face3D','boundary':[[x,y,z],...]}."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create an orphaned Honeybee Face."""
        from garden.honeybee_core.creation import create_honeybee_face as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            model_target=model_target,
        )

    @mcp.tool(
        name="HB_Create_Model",
        description=(
            'Create an empty Honeybee Model in a Garden and optionally set it as the base '
            'Honeybee model with set_base. A Honeybee Model is the upstream container for Rooms, '
            'Faces, Apertures, Doors, and Shades. Returns compact target/model_target fields for '
            'downstream calls; object_dict is a compact target when saved and a full model body '
            'only when save_back=false and include_body=true. Typically followed by '
            'HB_Create_Room for rooms (use add_objects when supplying complete Honeybee object '
            'dictionaries). Requires garden_root and identifier.'
        ),
        tags={
            "author",
            "honeybee",
            "model",
        },
        timeout=20,
    )
    def create_honeybee_model(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description="Required Honeybee model identifier used for the stable Garden HBJSON file name."
            ),
        ],
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
        save_back: Annotated[
            bool,
            Field(
                description="Whether to persist the Honeybee Model to the Garden and return Garden targets/receipt fields."
            ),
        ] = True,
        set_base: Annotated[
            bool,
            Field(
                description='Whether to set as the Garden base Honeybee model.'
            ),
        ] = True,
        include_body: Annotated[
            bool,
            Field(
                description="Whether to return the full Honeybee Model body when save_back is false; saved models return compact targets."
            ),
        ] = False,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Optional complete Honeybee Room, Face, Aperture, Door, or Shade object '
                    'dictionaries to include at creation (for typical modeling, omit and call '
                    'HB_Create_Room next).'
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Model."""
        from garden.honeybee_core.creation import create_honeybee_model as service

        if unit_system is not None:
            normalized_unit_system = unit_system.strip().lower()
            if normalized_unit_system in {"metric", "si"}:
                units = "Meters"
            elif normalized_unit_system in {"imperial", "ip"}:
                units = "Feet"
            else:
                units = unit_system
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
        )

    @mcp.tool(
        name="HB_Create_Room",
        description=(
            'Create a Honeybee Room, meaning a room/space envelope in a Garden Honeybee Model, '
            'from either a Honeybee Face list, a Ladybug Geometry Polyface3D envelope, or custom '
            'box dimensions. For simple boxes, pass x_dim, y_dim, height, and optional origin; '
            'the room attaches automatically as a top-level object on the selected model. '
            'Requires garden_root, identifier, and one geometry mode. Returns target, '
            'object_target, model_target, and room_target.'
        ),
        tags={
            "author",
            "geometry",
            "honeybee",
            "room",
        },
        timeout=20,
    )
    def create_honeybee_room(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str, Field(description="Required Honeybee room identifier.")
        ],
        faces: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Optional list of complete Honeybee Face dictionaries for the room. Must '
                    'provide one geometry mode.'
                )
            ),
        ] = None,
        room_geometry: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ladybug Geometry Polyface3D dictionary for the room envelope, for example Polyface3D.from_box(...).to_dict() with vertices and face_indices. Must provide exactly one geometry mode."
            ),
        ] = None,
        x_dim: Annotated[
            float | None,
            Field(
                description="Optional custom box width. Use with y_dim and height as one geometry mode."
            ),
        ] = None,
        y_dim: Annotated[
            float | None,
            Field(
                description="Optional custom box depth. Use with x_dim and height as one geometry mode."
            ),
        ] = None,
        height: Annotated[
            float | None,
            Field(
                description="Optional custom box height. Use with x_dim and y_dim as one geometry mode."
            ),
        ] = None,
        origin: Annotated[
            list[float] | dict[str, Any] | None,
            Field(
                description="Optional box origin as [x, y, z] or {x, y, z}. Defaults to [0, 0, 0]."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Honeybee model target dict from HB_Create_Model; defaults to the '
                    'Garden base Honeybee Model.'
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create a Honeybee Room."""
        from garden.honeybee_core.creation import create_honeybee_room as service

        origin_value = origin
        if isinstance(origin_value, dict):
            origin_value = [
                float(origin_value.get("x", 0)),
                float(origin_value.get("y", 0)),
                float(origin_value.get("z", 0)),
            ]
        return service(
            garden_root=garden_root,
            identifier=identifier,
            faces=faces,
            room_geometry=room_geometry,
            x_dim=x_dim,
            y_dim=y_dim,
            height=height,
            origin=origin_value,
            model_target=model_target,
        )

    @mcp.tool(
        name="HB_Create_Shade",
        description=(
            'Create an orphaned Honeybee Shade or attach it to a Room, Face, Aperture, or Door '
            'typed target from explicit Face3D geometry. This is the low-level explicit-geometry '
            'route for context shades, hosted shades, custom sunshades, or overhangs that already '
            'have Face3D geometry. For parametric louvers or aperture extruded borders, use '
            'HB_Create_Shades_By_Parameters instead. Requires garden_root, unique identifier, and '
            'geometry; hosted shades also need host_target from HB_Search_Model_Objects '
            'matches[i].target or a prior result target. Returns target, object_target, '
            'model_target, shade_target, summary_view, persistence_receipt, and report.'
        ),
        tags={
            "author",
            "geometry",
            "honeybee",
            "hosted",
            "shade",
        },
        timeout=20,
    )
    def create_honeybee_shade(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        identifier: Annotated[
            str,
            Field(
                description='Required unique Honeybee shade identifier. If it already exists, use HB_Search_Model_Objects to reuse/remove it or choose a new identifier.'
            ),
        ],
        geometry: Annotated[
            dict[str, Any],
            Field(
                description=(
                    'Required Ladybug Geometry Face3D dict, for example '
                    "{'type':'Face3D','boundary':[[x,y,z],...]}; boundary points may also be "
                    "{'x':0,'y':0,'z':0} Point3D dicts. Omit plane unless providing Ladybug Plane "
                    'keys n, o, and x.'
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        host_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Honeybee room, face, aperture, or door typed target dict from '
                    'HB_Search_Model_Objects matches[i].target or a prior create result; omit for '
                    'an orphaned shade.'
                )
            ),
        ] = None,
        attach_side: Annotated[
            str,
            Field(
                description="Attach side for hosted shades: outdoor or indoor. Natural exterior words like top, exterior, or outside normalize to outdoor."
            ),
        ] = "outdoor",
        is_detached: Annotated[
            bool, Field(description="Whether the shade is detached.")
        ] = False,
    ) -> dict[str, Any]:
        """Create a Honeybee Shade."""
        from garden.honeybee_core.creation import create_honeybee_shade as service

        return service(
            garden_root=garden_root,
            identifier=identifier,
            geometry=geometry,
            model_target=model_target,
            host_target=host_target,
            attach_side=attach_side,
            is_detached=is_detached,
        )

    @mcp.tool(
        name="HB_Create_Shades_By_Parameters",
        description=(
            'Create Honeybee Shade louvers, horizontal louver arrays, or aperture extruded '
            'borders on a Face or Aperture typed target. This is the parametric shade path for '
            'louver_by_count, louver_by_distance_between, and aperture-only extruded_border; it '
            'does not expose a parametric overhang mode. Use HB_Create_Shade only when the user '
            'provides explicit Face3D geometry. Prefer HB_Search_Model_Objects matches[i].target '
            'or a prior result target as host_target. Requires garden_root, host_target, '
            'generation_mode, and parameters. Returns target, shade_target, targets, '
            'summary_view, persistence_receipt, and report.'
        ),
        tags={
            "aperture",
            "author",
            "extruded-border",
            "face",
            "geometry",
            "honeybee",
            "hosted",
            "louver",
            "shade",
        },
        timeout=20,
    )
    def create_honeybee_shades_by_parameters(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description="Required Honeybee face or aperture typed target dict from HB_Search_Model_Objects matches[i].target or a prior create result."
            ),
        ],
        generation_mode: Annotated[
            str | None,
            Field(
                description="Required generation mode: louver_by_count, louver_by_distance_between, or extruded_border. extruded_border only accepts an aperture target."
            ),
        ] = None,
        parameters: Annotated[
            dict[str, Any] | None,
            Field(
                description="Required small mode parameter object: louver_by_count uses {'depth':0.35,'louver_count':2}; louver_by_distance_between uses {'depth':0.35,'distance':0.5}; extruded_border uses {'depth':0.2}. Optional base_name may guide generated Shade identifiers."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create Honeybee Shades on a Face or Aperture with SDK parameter methods."""
        from garden.honeybee_core.creation import (
            create_honeybee_shades_by_parameters as service,
        )

        return service(
            garden_root=garden_root,
            host_target=host_target,
            generation_mode=generation_mode,
            parameters=parameters,
            model_target=model_target,
        )

    @mcp.tool(
        name="HB_Create_Skylights_By_Ratio",
        description=(
            "Create or reuse Honeybee skylight Apertures on a RoofCeiling or "
            "Floor Face typed target by an aperture-to-face area ratio. The Face "
            "must have an Outdoors boundary condition. Existing compatible "
            "Apertures are returned without a new write; existing Doors or a "
            "different aperture ratio are rejected because the Honeybee SDK ratio "
            "generator replaces sub-faces. Use HB_Create_Aperture for explicit "
            "Face3D geometry. Returns target, aperture_target, targets, "
            "summary_view, persistence_receipt, and report."
        ),
        tags={
            "aperture",
            "author",
            "face",
            "floor",
            "honeybee",
            "ratio",
            "roof",
            "skylight",
        },
        timeout=20,
    )
    def create_honeybee_skylights_by_ratio(
        garden_root: Annotated[
            str,
            Field(
                description=(
                    "Required Garden root path containing garden.json, usually "
                    "GD_Create['garden_root']."
                )
            ),
        ],
        host_target: Annotated[
            dict[str, Any],
            Field(
                description=(
                    "Required Honeybee Face typed target from "
                    "HB_Search_Model_Objects; it must identify a RoofCeiling or "
                    "Floor Face with an Outdoors boundary condition."
                )
            ),
        ],
        ratio: Annotated[
            float,
            Field(
                description=(
                    "Required aperture-to-face area ratio between 0 and 1, for "
                    "example 0.2."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    "Optional Honeybee model target dict; defaults to the Garden "
                    "base Honeybee Model."
                )
            ),
        ] = None,
        tolerance: Annotated[
            float,
            Field(description="Positive geometry and ratio matching tolerance."),
        ] = 0.01,
        identifier_prefix: Annotated[
            str | None,
            Field(
                description="Optional prefix for generated skylight identifiers."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Create or reuse ratio-based skylights on a Honeybee Face."""
        from garden.honeybee_core.creation import (
            create_honeybee_skylights_by_ratio as service,
        )

        return service(
            garden_root=garden_root,
            host_target=host_target,
            ratio=ratio,
            model_target=model_target,
            tolerance=tolerance,
            identifier_prefix=identifier_prefix,
        )

    @mcp.tool(
        name="HB_Edit_Aperture",
        description=(
            'Edit a Honeybee Aperture/window typed target for display name, user data, supported '
            'Face3D geometry, operable flag, Honeybee Energy window construction or '
            'VentilationOpening, and Honeybee Radiance modifier/dynamic states. Surface-adjacent '
            'interior Apertures do not support single-side geometry or operability edits. '
            'Requires garden_root and a typed aperture target. Returns target, '
            'summary_view.updated_fields, persistence_receipt, and report for re-search, '
            'validation, or downstream Energy/Radiance translation.'
        ),
        tags={
            "aperture",
            "edit",
            "energy",
            "geometry",
            "honeybee",
            "modifier",
            "operable-window",
            "radiance",
            "surface",
            "ventilation-opening",
            "window",
        },
        timeout=20,
    )
    def edit_honeybee_aperture(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee aperture typed target from HB_Search_Model_Objects.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
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
                description=(
                    'Optional Ladybug Geometry Face3D dict, for example '
                    "{'type':'Face3D','boundary':[[x,y,z],...]}."
                )
            ),
        ] = None,
        is_operable: Annotated[
            bool | None, Field(description="Optional updated is_operable flag for supported Apertures; Surface-adjacent interior Apertures cannot be edited one side at a time.")
        ] = None,
        construction: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy window construction dictionary or Garden Properties Library construction target to attach or replace."
            ),
        ] = None,
        vent_opening: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy VentilationOpening dictionary to attach or replace."
            ),
        ] = None,
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from RAD_Search_Library_Objects.'
            ),
        ] = None,
        modifier_blk: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance black modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from RAD_Search_Library_Objects.'
            ),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Radiance dynamic group identifier."),
        ] = None,
        states: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description="Optional Honeybee Radiance state update. Accepts a state list for replace_all, or a dict with operation=replace_all|add|clear and states=[...]."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Honeybee Aperture."""
        from garden.honeybee_core.edit import edit_honeybee_aperture as service

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            geometry=geometry,
            is_operable=is_operable,
            construction=construction,
            vent_opening=vent_opening,
            modifier=modifier,
            modifier_blk=modifier_blk,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states,
        )

    @mcp.tool(
        name="HB_Edit_Door",
        description='Edit a Honeybee Door typed target for display name, user data, supported Face3D geometry, glass flag, Honeybee Energy door construction or VentilationOpening, and Honeybee Radiance modifier/dynamic states. Surface-adjacent interior Door geometry updates are paired automatically on the adjacent Door, but single-side is_glass changes are rejected when paired state would diverge. Returns target, summary_view.updated_fields, persistence_receipt, and report for re-search, validation, or downstream Energy/Radiance translation.',
        tags={
            "door",
            "edit",
            "energy",
            "geometry",
            "glass-door",
            "hosted",
            "honeybee",
            "interior-door",
            "radiance",
            "surface",
            "ventilation-opening",
        },
        timeout=20,
    )
    def edit_honeybee_door(
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
                    'Required Honeybee door typed target from HB_Search_Model_Objects. For '
                    'Surface-adjacent interior doors, pass either side of the pair and geometry '
                    'edits update the paired adjacent Door automatically.'
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
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
                description=(
                    'Optional Ladybug Geometry Face3D dict, for example '
                    "{'type':'Face3D','boundary':[[x,y,z],...]}."
                )
            ),
        ] = None,
        is_glass: Annotated[
            bool | None, Field(description="Optional updated is_glass flag; Surface-adjacent interior door pairs cannot be changed to divergent glass states.")
        ] = None,
        construction: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy door construction dictionary or Garden Properties Library construction target to attach or replace."
            ),
        ] = None,
        vent_opening: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy VentilationOpening dictionary to attach or replace."
            ),
        ] = None,
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from RAD_Search_Library_Objects.'
            ),
        ] = None,
        modifier_blk: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance black modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from RAD_Search_Library_Objects.'
            ),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Radiance dynamic group identifier."),
        ] = None,
        states: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description="Optional Honeybee Radiance state update. Accepts a state list for replace_all, or a dict with operation=replace_all|add|clear and states=[...]."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Honeybee Door."""
        from garden.honeybee_core.edit import edit_honeybee_door as service

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            geometry=geometry,
            is_glass=is_glass,
            construction=construction,
            vent_opening=vent_opening,
            modifier=modifier,
            modifier_blk=modifier_blk,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states,
        )

    @mcp.tool(
        name="HB_Edit_Face",
        description=(
            'Edit a Honeybee Face typed target for display name, user data, Face3D geometry, face '
            'type, non-Surface boundary condition, Honeybee Energy construction/AFNCrack, and '
            'Honeybee Radiance modifier or black modifier. Geometry edits are for supported Face '
            'targets and must respect hosted sub-face and shade constraints. Returns target, '
            'summary_view.updated_fields, persistence_receipt, and report for re-search, '
            'validation, or downstream Energy/Radiance translation.'
        ),
        tags={
            "boundary-condition",
            "construction",
            "edit",
            "energy",
            "face",
            "geometry",
            "honeybee",
            "modifier",
            "radiance",
            "wall",
        },
        timeout=20,
    )
    def edit_honeybee_face(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee face typed target from HB_Search_Model_Objects.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
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
                description=(
                    'Optional Ladybug Geometry Face3D dict, for example '
                    "{'type':'Face3D','boundary':[[x,y,z],...]}."
                )
            ),
        ] = None,
        type: Annotated[
            str | dict[str, Any] | None,
            Field(description="Optional updated Honeybee Face type name or dict."),
        ] = None,
        boundary_condition: Annotated[
            str | dict[str, Any] | None,
            Field(
                description=(
                    'Optional updated Honeybee boundary condition name or dict. Use '
                    'HB_Relate_Model for Surface adjacency solving.'
                )
            ),
        ] = None,
        construction: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy opaque construction dictionary or Garden Properties Library construction target to attach or replace."
            ),
        ] = None,
        vent_crack: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy AFNCrack dictionary to attach or replace."
            ),
        ] = None,
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from RAD_Search_Library_Objects.'
            ),
        ] = None,
        modifier_blk: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance black modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from RAD_Search_Library_Objects.'
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Honeybee Face."""
        from garden.honeybee_core.edit import edit_honeybee_face as service

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            geometry=geometry,
            type=type,
            boundary_condition=boundary_condition,
            construction=construction,
            vent_crack=vent_crack,
            modifier=modifier,
            modifier_blk=modifier_blk,
        )

    @mcp.tool(
        name="HB_Edit_Model",
        description=(
            'Edit a Honeybee Model display name, user data, units, tolerances, model-level Energy '
            'electric load center, complete object-dict additions/removals, and existing Radiance '
            'SensorGrid/View attachments while preserving its Garden persistence path. Requires '
            'garden_root and a Honeybee model target; pass complete Honeybee object dictionaries '
            'to add_objects (rooms from HB_Create_Room are already attached). Returns target, '
            'model_target, summary_view, persistence_receipt, report, and optional radiance '
            'attachment summaries for downstream search, validation, visualization, Radiance, or '
            'EnergyPlus calls.'
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
        timeout=20,
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
                    'Required Honeybee model target dict from HB_Create_Model, '
                    'GD_Get_Base_Honeybee_Model, or GD_List_Models.'
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
        tolerance: Annotated[
            float | None, Field(description="Optional updated model tolerance.")
        ] = None,
        angle_tolerance: Annotated[
            float | None, Field(description="Optional updated model angle tolerance.")
        ] = None,
        electric_load_center: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional Honeybee Energy ElectricLoadCenter dict or Garden Properties Library electric_load_center target from EP_Create_Electric_Load_Center, used for PV inverter/load-center settings.'
            ),
        ] = None,
        add_objects: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description=(
                    'Optional complete Honeybee Room, Face, Aperture, Door, or Shade object '
                    'dictionaries to append to the model.'
                )
            ),
        ] = None,
        add_sensor_grids: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description='Optional list of existing radiance_sensor_grid target dicts to attach to Honeybee Model Radiance properties. Prefer RAD_Create_Sensor_Grid attach_to_model=true when creating new grids.'
            ),
        ] = None,
        radiance_sensor_grid_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional single radiance_sensor_grid target dict; converted into add_sensor_grids=[target]."),
        ] = None,
        add_radiance_views: Annotated[
            list[dict[str, Any]] | None,
            Field(description='Optional list of existing radiance_view target dicts to attach to Honeybee Model Radiance properties. Prefer RAD_Create_View attach_to_model=true when creating new views.'),
        ] = None,
        radiance_view_target: Annotated[
            dict[str, Any] | None,
            Field(description="Optional single radiance_view target dict; converted into add_radiance_views=[target]."),
        ] = None,
        remove_targets: Annotated[
            list[dict[str, Any]] | None,
            Field(
                description='Optional Honeybee typed targets from HB_Search_Model_Objects to remove from the model. Only top-level Room and orphaned Face, Aperture, Door, and Shade targets are supported.'
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
        result: dict[str, Any]
        if has_core_edits:
            result = service(
                garden_root=garden_root,
                target=target,
                display_name=display_name,
                user_data=user_data,
                units=units,
                tolerance=tolerance,
                angle_tolerance=angle_tolerance,
                electric_load_center=electric_load_center,
                add_objects=add_objects,
                remove_targets=remove_targets,
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
        name="HB_Edit_Room",
        description=(
            'Edit a Honeybee Room display name, story, zone, multiplier, floor-area flag, '
            'Honeybee Energy ProgramType/ConstructionSet/HVAC-template/ventilation/setpoint '
            'properties, and Honeybee Radiance ModifierSet in a Garden model. Use target from '
            'HB_Search_Model_Objects matches[i].target or HB_Create_Room.target; an exact '
            'same-model room identifier string is accepted only with the intended model_target. '
            'Returns target, summary_view.updated_fields, persistence_receipt, and report for '
            'later search, validation, EnergyPlus translation, or Radiance workflows.'
        ),
        tags={
            "construction-set",
            "edit",
            "energy",
            "honeybee",
            "hvac-template",
            "modifier-set",
            "program-type",
            "radiance",
            "room",
            "setpoint",
            "ventilation",
        },
        timeout=20,
    )
    def edit_honeybee_room(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any] | str,
            Field(
                description=(
                    "Required Honeybee room typed target dict from "
                    'HB_Search_Model_Objects matches[i].target or '
                    'HB_Create_Room.target. Also accepts an exact '
                    "same-model room identifier string when model_target "
                    "selects the intended Honeybee Model."
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
        display_name: Annotated[
            str | None, Field(description="Optional updated display name.")
        ] = None,
        user_data: Annotated[
            dict[str, Any] | None,
            Field(description="Optional replacement user_data dictionary."),
        ] = None,
        multiplier: Annotated[
            int | None,
            Field(description="Optional updated room multiplier. Must be >= 1."),
        ] = None,
        zone: Annotated[
            str | None, Field(description='Optional updated Honeybee Room zone name.')
        ] = None,
        story: Annotated[
            str | None, Field(description="Optional updated story name.")
        ] = None,
        exclude_floor_area: Annotated[
            bool | None, Field(description="Optional updated exclude_floor_area flag.")
        ] = None,
        program_type: Annotated[
            dict[str, Any] | str | None,
            Field(
                description=(
                    'Optional Honeybee Energy ProgramType dict, Garden target, or exact standards '
                    'library identifier from EP_Search_Energy_Library_Objects '
                    'matches[i].identifier, for example Generic Office Program.'
                )
            ),
        ] = None,
        construction_set: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Energy ConstructionSet dict, Garden target, or exact standards library identifier to attach or replace. Prefer EP_Create_Construction_Set.target for custom sets.'
            ),
        ] = None,
        hvac: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Honeybee Energy HVAC dict or Garden Properties Library hvac target '
                    'from EP_Create_Ideal_Air_System or EP_Search_HVAC_Templates.'
                )
            ),
        ] = None,
        ventilation: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy Ventilation dict or Garden Properties Library load target."
            ),
        ] = None,
        zone_ventilation_fans: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description='Optional zone ventilation fan collection update for Room.properties.energy.fans. Accepts a Garden Properties Library zone_ventilation_fan target, a list of fan dicts/targets for replace_all, or {operation: replace_all|add|clear, fans:[...]} from EP_Create_Zone_Ventilation_Fan. This is fan-assisted/mechanical zone ventilation, not operable-window natural ventilation.'
            ),
        ] = None,
        setpoint: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional Honeybee Energy Setpoint dict (lightweight schedule identifiers '
                    'supported) or Garden Properties Library target from '
                    'EP_Create_Setpoint.target.'
                )
            ),
        ] = None,
        modifier_set: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Radiance ModifierSet dictionary or Garden Properties Library modifier_set target to attach or replace."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Honeybee Room."""
        from garden.honeybee_core.edit import edit_honeybee_room as service

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            multiplier=multiplier,
            zone=zone,
            story=story,
            exclude_floor_area=exclude_floor_area,
            program_type=program_type,
            construction_set=construction_set,
            hvac=hvac,
            ventilation=ventilation,
            zone_ventilation_fans=zone_ventilation_fans,
            setpoint=setpoint,
            modifier_set=modifier_set,
        )

    @mcp.tool(
        name="HB_Edit_Shade",
        description='Edit a Honeybee Shade typed target for display name, user data, supported Face3D geometry, detached flag on orphaned shades, Honeybee Energy ShadeConstruction/transmittance schedule/PVProperties, and Honeybee Radiance modifier/dynamic states. Hosted shades keep their parent relationship and cannot be made detached by setting is_detached=true. Returns target, summary_view.updated_fields, persistence_receipt, and report for re-search, validation, or downstream Energy/Radiance translation.',
        tags={
            "detached-shade",
            "edit",
            "energy",
            "geometry",
            "hosted",
            "honeybee",
            "pv",
            "radiance",
            "shade",
            "shading",
            "transmittance-schedule",
        },
        timeout=20,
    )
    def edit_honeybee_shade(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee shade typed target from HB_Search_Model_Objects.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
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
                description=(
                    'Optional Ladybug Geometry Face3D dict, for example '
                    "{'type':'Face3D','boundary':[[x,y,z],...]}."
                )
            ),
        ] = None,
        is_detached: Annotated[
            bool | None,
            Field(description="Optional updated detached flag for orphaned shades only; hosted shades cannot be detached in place."),
        ] = None,
        construction: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy ShadeConstruction dictionary or Garden Properties Library construction target to attach or replace."
            ),
        ] = None,
        transmittance_schedule: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee Energy schedule dictionary or Garden Properties Library schedule target for shade transmittance."
            ),
        ] = None,
        pv_properties: Annotated[
            dict[str, Any] | None,
            Field(
                description='Optional Honeybee Energy PVProperties dictionary or Garden Properties Library pv_properties target from EP_Create_PV_Properties to attach or replace.'
            ),
        ] = None,
        modifier: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from RAD_Search_Library_Objects.'
            ),
        ] = None,
        modifier_blk: Annotated[
            dict[str, Any] | str | None,
            Field(
                description='Optional Honeybee Radiance black modifier dictionary, Garden Properties Library modifier target, or standards-library modifier identifier from RAD_Search_Library_Objects.'
            ),
        ] = None,
        dynamic_group_identifier: Annotated[
            str | None,
            Field(description="Optional Honeybee Radiance dynamic group identifier."),
        ] = None,
        states: Annotated[
            dict[str, Any] | list[dict[str, Any]] | None,
            Field(
                description="Optional Honeybee Radiance state update. Accepts a state list for replace_all, or a dict with operation=replace_all|add|clear and states=[...]."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Edit a Honeybee Shade."""
        from garden.honeybee_core.edit import edit_honeybee_shade as service

        return service(
            garden_root=garden_root,
            target=target,
            model_target=model_target,
            display_name=display_name,
            user_data=user_data,
            geometry=geometry,
            is_detached=is_detached,
            construction=construction,
            transmittance_schedule=transmittance_schedule,
            pv_properties=pv_properties,
            modifier=modifier,
            modifier_blk=modifier_blk,
            dynamic_group_identifier=dynamic_group_identifier,
            states=states,
        )

    @mcp.tool(
        name="HB_Import_Model_File",
        description=(
            "Import a Garden-local Honeybee HBJSON file and save it as a Honeybee "
            "model target. The file path must be relative to the Garden; the full "
            "model body is not returned."
        ),
        tags={"author", "honeybee", "model", "hbjson", "import", "garden"},
        timeout=60,
    )
    def import_honeybee_model_file(
        garden_root: Annotated[
            str, Field(description="Required Garden root path containing garden.json.")
        ],
        file_path: Annotated[
            str, Field(description="Garden-relative .hbjson file path to import.")
        ],
        identifier: Annotated[
            str | None, Field(description="Optional identifier for the stored model.")
        ] = None,
        set_base: Annotated[
            bool,
            Field(description="Whether to set the imported model as the base Honeybee model."),
        ] = True,
    ) -> dict[str, Any]:
        """Import a Honeybee HBJSON model file."""
        from garden.honeybee_core.model_io import import_honeybee_model_file as service

        return service(
            garden_root=garden_root,
            file_path=file_path,
            identifier=identifier,
            set_base=set_base,
        )

    @mcp.tool(
        name="HB_Mirror_Object",
        description=(
            'Mirror, or reflect, a Honeybee Model, Room, Face, Aperture, Door, or Shade target '
            'across a Ladybug Geometry Plane. This transform does not automatically repair '
            'adjacency, host containment, or dynamic state geometry. Requires a typed target and '
            'plane dict. Returns the original target, summary_view, persistence_receipt with '
            'updated model_target, and report; for whole-model transforms summary_view.target is '
            'the updated model target. Run HB_Search_Model_Objects, HB_Relate_Model, or '
            'HB_Validate_Model after partial-object transforms when relationships matter.'
        ),
        tags={
            "edit",
            "geometry",
            "honeybee",
            "mirror",
            "model",
            "target",
            "transform",
        },
        timeout=20,
    )
    def mirror_object(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee model target or object typed target from HB_Search_Model_Objects or a prior tool result.'
            ),
        ],
        plane: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Plane dict with origin o and normal n, for example {'o':[0,0,0],'n':[1,0,0]}."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model unless target is a model target."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Reflect a Honeybee target across a Plane."""
        from garden.honeybee_core.transform import mirror_object as service

        return service(
            garden_root=garden_root,
            target=target,
            plane=plane,
            model_target=model_target,
        )

    @mcp.tool(
        name="HB_Move_Object",
        description=(
            'Move a Honeybee Model, Room, Face, Aperture, Door, or Shade target along a Ladybug '
            'Geometry Vector3D. This transform does not automatically repair adjacency, host '
            'containment, or dynamic state geometry. Requires garden_root, a typed target from '
            'search or a prior result, and vector. Returns the original target, summary_view, '
            'persistence_receipt with updated model_target, and report; for whole-model '
            'transforms summary_view.target is the updated model target. Run '
            'HB_Search_Model_Objects, HB_Relate_Model, or HB_Validate_Model after partial-object '
            'transforms when relationships matter.'
        ),
        tags={
            "edit",
            "geometry",
            "honeybee",
            "model",
            "move",
            "target",
            "transform",
        },
        timeout=20,
    )
    def move_object(
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
                    'Required Honeybee model target or object typed target from '
                    'HB_Search_Model_Objects or a prior tool result.'
                )
            ),
        ],
        vector: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Vector3D dict, for example {'type':'Vector3D','x':0.5,'y':0,'z':0} or {'x':0.5,'y':0,'z':0}."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model unless target is a model target."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Move a Honeybee target along a Vector3D."""
        from garden.honeybee_core.transform import move_object as service

        return service(
            garden_root=garden_root,
            target=target,
            vector=vector,
            model_target=model_target,
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
        name="HB_Remove_Aperture",
        description='Remove one Honeybee Aperture/window from a Garden model using an aperture typed target from HB_Search_Model_Objects and persist the updated model. Hosted Apertures are supported; when the target is one side of a Surface-adjacent interior pair, the paired Aperture can be removed too and reported as paired_removed_identifier with removed_count=2. Returns summary_view.model_target, persistence_receipt.model_target, and report so the updated model can be searched or validated again.',
        tags={
            "aperture",
            "edit",
            "hosted",
            "honeybee",
            "interior-window",
            "paired-window",
            "remove",
            "surface",
            "target",
            "window",
        },
        timeout=20,
    )
    def remove_honeybee_aperture(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee aperture typed target from HB_Search_Model_Objects.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Aperture by typed target."""
        from garden.honeybee_core.removal import remove_honeybee_aperture as service

        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )

    @mcp.tool(
        name="HB_Remove_Door",
        description='Remove one Honeybee Door from a Garden model using a door typed target from HB_Search_Model_Objects and persist the updated model. Hosted Doors are supported; when the target is one side of a Surface-adjacent interior pair, the paired Door can be removed too and reported as paired_removed_identifier with removed_count=2. Returns summary_view.model_target, persistence_receipt.model_target, and report so the updated model can be searched or validated again.',
        tags={
            "door",
            "edit",
            "hosted",
            "honeybee",
            "interior-door",
            "paired-door",
            "remove",
            "surface",
            "target",
        },
        timeout=20,
    )
    def remove_honeybee_door(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee door typed target from HB_Search_Model_Objects.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Door by typed target."""
        from garden.honeybee_core.removal import remove_honeybee_door as service

        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )

    @mcp.tool(
        name="HB_Remove_Face",
        description=(
            'Remove one orphaned Honeybee Face from a Garden model using a face typed target from '
            'HB_Search_Model_Objects and persist the updated model. Room-hosted Faces are '
            'rejected because deleting one would break the Room closed solid. Requires '
            'garden_root and a typed target. Returns summary_view.model_target, '
            'persistence_receipt.model_target, and report so the updated model can be searched or '
            'validated again.'
        ),
        tags={
            "edit",
            "face",
            "geometry",
            "honeybee",
            "orphaned-face",
            "remove",
            "target",
        },
        timeout=20,
    )
    def remove_honeybee_face(
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
                    'Required Honeybee face typed target from HB_Search_Model_Objects. '
                    'Room-hosted faces cannot be removed by this tool.'
                )
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Face by typed target."""
        from garden.honeybee_core.removal import remove_honeybee_face as service

        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )

    @mcp.tool(
        name="HB_Remove_Room",
        description=(
            'Remove one Honeybee Room from a Garden model using a room typed target from '
            'HB_Search_Model_Objects and persist the updated model. This also clears Surface '
            'boundary relationships in remaining rooms that pointed to the removed room and '
            'reports adjacency_cleanup. Requires garden_root and a typed target. Returns '
            'summary_view.model_target, persistence_receipt.model_target, and report so the '
            'updated model can be searched or validated again.'
        ),
        tags={
            "adjacency",
            "boundary",
            "cleanup",
            "edit",
            "honeybee",
            "remove",
            "room",
            "target",
        },
        timeout=20,
    )
    def remove_honeybee_room(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee room typed target from HB_Search_Model_Objects.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Room by typed target."""
        from garden.honeybee_core.removal import remove_honeybee_room as service

        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )

    @mcp.tool(
        name="HB_Remove_Shade",
        description=(
            'Remove one Honeybee Shade from a Garden model using a shade typed target from '
            'HB_Search_Model_Objects and persist the updated model. Orphaned and hosted shades '
            'are supported, including Room, Face, Aperture, and Door child shade contexts; the '
            'service removes the child from its parent list where needed. Requires garden_root '
            'and a typed target. Returns summary_view.model_target, '
            'persistence_receipt.model_target, and report so the updated model can be searched or '
            'validated again.'
        ),
        tags={
            "edit",
            "hosted",
            "hosted-shade",
            "honeybee",
            "remove",
            "shade",
            "shading",
            "target",
        },
        timeout=20,
    )
    def remove_honeybee_shade(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee shade typed target from HB_Search_Model_Objects.'
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Remove a Honeybee Shade by typed target."""
        from garden.honeybee_core.removal import remove_honeybee_shade as service

        return service(
            garden_root=garden_root, target=target, model_target=model_target
        )

    @mcp.tool(
        name="HB_Rotate_Object",
        description=(
            'Rotate a Honeybee Model, Room, Face, Aperture, Door, or Shade target around a '
            'Ladybug Geometry Vector3D axis and Point3D origin, with angle_degrees in degrees. '
            'This transform does not automatically repair adjacency, host containment, or dynamic '
            'state geometry. Requires a typed target plus axis and origin dicts. Returns the '
            'original target, summary_view, persistence_receipt with updated model_target, and '
            'report; for whole-model transforms summary_view.target is the updated model target. '
            'Run HB_Search_Model_Objects, HB_Relate_Model, or HB_Validate_Model after '
            'partial-object transforms when relationships matter.'
        ),
        tags={
            "edit",
            "geometry",
            "honeybee",
            "model",
            "rotate",
            "target",
            "transform",
        },
        timeout=20,
    )
    def rotate_object(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee model target or object typed target from HB_Search_Model_Objects or a prior tool result.'
            ),
        ],
        axis: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Vector3D axis dict, for example {'x':0,'y':0,'z':1}."
            ),
        ],
        angle_degrees: Annotated[
            float, Field(description="Required rotation angle in degrees.")
        ],
        origin: Annotated[
            dict[str, Any],
            Field(
                description="Required Ladybug Geometry Point3D origin dict, for example {'x':0,'y':0,'z':0}."
            ),
        ],
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model unless target is a model target."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Rotate a Honeybee target around an axis and origin."""
        from garden.honeybee_core.transform import rotate_object as service

        return service(
            garden_root=garden_root,
            target=target,
            axis=axis,
            angle_degrees=angle_degrees,
            origin=origin,
            model_target=model_target,
        )

    @mcp.tool(
        name="HB_Scale_Object",
        description=(
            'Scale a Honeybee Model, Room, Face, Aperture, Door, or Shade target by a positive '
            'factor from an optional Ladybug Geometry Point3D origin. This transform does not '
            'automatically repair adjacency, host containment, or dynamic state geometry. '
            'Requires a typed target and positive factor. Returns the original target, '
            'summary_view, persistence_receipt with updated model_target, and report; for '
            'whole-model transforms summary_view.target is the updated model target. Run '
            'HB_Search_Model_Objects, HB_Relate_Model, or HB_Validate_Model after partial-object '
            'transforms when relationships matter.'
        ),
        tags={
            "edit",
            "geometry",
            "honeybee",
            "model",
            "scale",
            "target",
            "transform",
        },
        timeout=20,
    )
    def scale_object(
        garden_root: Annotated[
            str,
            Field(
                description="Required Garden root path containing garden.json, usually GD_Create['garden_root']."
            ),
        ],
        target: Annotated[
            dict[str, Any],
            Field(
                description='Required Honeybee model target or object typed target from HB_Search_Model_Objects or a prior tool result.'
            ),
        ],
        factor: Annotated[
            float, Field(description="Required positive scale factor, for example 1.2.")
        ],
        origin: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Ladybug Geometry Point3D origin dict, for example {'x':0,'y':0,'z':0}. Defaults to world origin."
            ),
        ] = None,
        model_target: Annotated[
            dict[str, Any] | None,
            Field(
                description="Optional Honeybee model target dict, usually HB_Create_Model['target']; defaults to the Garden base Honeybee Model unless target is a model target."
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Scale a Honeybee target from an optional origin."""
        from garden.honeybee_core.transform import scale_object as service

        return service(
            garden_root=garden_root,
            target=target,
            factor=factor,
            origin=origin,
            model_target=model_target,
        )

    @mcp.tool(
        name="HB_Search_Model_Objects",
        description=(
            'Search Honeybee Room, Face, Aperture/window, Door, and Shade objects in the Garden '
            'base model or an explicit model_target. Use object_type plus identifier, query, '
            'room_identifier, face_identifier, face_type, boundary_condition, or children_scope '
            'to narrow results; for exterior wall/window workflows search faces with '
            'face_type=Wall and boundary_condition=Outdoors, then search children under the face. '
            'Returns matches with nested target dicts, compact child_counts, geometry summaries, '
            'limited room/shade energy_properties, summary_view, and a top-level target only when '
            'there is one match. Pass matches[i].target to create/edit/remove tools.'
        ),
        tags={
            "aperture",
            "children",
            "door",
            "face",
            "honeybee",
            "model",
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
                description=(
                    "Optional Honeybee model target dict, usually HB_Create_Model['target']; "
                    'defaults to the Garden base Honeybee Model.'
                )
            ),
        ] = None,
        object_type: Annotated[
            str,
            Field(
                description="Object type to return: all, room, face, aperture, door, or shade. Use room for rooms, face for walls, aperture for windows, door for doors, and shade for shades."
            ),
        ] = "all",
        identifier: Annotated[
            str | None,
            Field(
                description="Optional exact Honeybee object identifier or display name filter, such as office_west or office_west_Front."
            ),
        ] = None,
        room_identifier: Annotated[
            str | None,
            Field(
                description="Optional parent room identifier filter for faces, apertures, doors, or shades, such as office_west."
            ),
        ] = None,
        face_identifier: Annotated[
            str | None,
            Field(
                description="Optional parent face identifier filter for apertures, doors, or shades, such as office_west_Front. For object_type=face, it filters the face identifier itself."
            ),
        ] = None,
        query: Annotated[
            str | None,
            Field(
                description="Optional identifier/display-name substring query, such as Tiny_House_Office or Front exterior wall."
            ),
        ] = None,
        face_type: Annotated[
            str | None,
            Field(
                description="Optional face type filter for face searches, for example Wall, Floor, RoofCeiling, or AirBoundary."
            ),
        ] = None,
        boundary_condition: Annotated[
            str | dict[str, Any] | None,
            Field(
                description="Optional boundary condition filter for face/aperture/door searches, for example Outdoors or {type: Outdoors}."
            ),
        ] = None,
        children_scope: Annotated[
            dict[str, Any] | None,
            Field(
                description=(
                    'Optional typed Honeybee parent target dict (room, face, aperture, or door) '
                    'to filter returned child objects.'
                )
            ),
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

        object_type = object_type.strip().lower().replace("-", "_").replace(" ", "_")
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
            limit=limit,
        )

    @mcp.tool(
        name="HB_Validate_Model",
        description=(
            'Validate an existing Honeybee model in a Garden using Honeybee Model.check_all '
            '(read-only). Returns is_valid/valid, issues, summary_view, and report.'
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
                    'defaults to the Garden base Honeybee Model.'
                )
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Validate a Honeybee model and return structured issues."""
        from garden.honeybee_core.model_io import (
            validate_honeybee_model as service,
        )

        return service(garden_root=garden_root, model_target=model_target)
