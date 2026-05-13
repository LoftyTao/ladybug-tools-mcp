"""Dragonfly Energy/Radiance properties summary services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import dragonfly_energy._extend_dragonfly  # noqa: F401
import dragonfly_radiance._extend_dragonfly  # noqa: F401
import dragonfly_uwg._extend_dragonfly  # noqa: F401
from dragonfly_radiance.gridpar import (
    ExteriorApertureGridParameter,
    ExteriorFaceGridParameter,
    RoomGridParameter,
    RoomRadialGridParameter,
)
from honeybee_energy.lib.constructionsets import construction_set_by_identifier
from honeybee_energy.lib.programtypes import program_type_by_identifier
from honeybee_radiance.lib.modifiersets import modifier_set_by_identifier
from ladybug_geometry.geometry3d import Vector3D

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_core.targets import normalize_dragonfly_object_target
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


_ENERGY_MODEL_LIST_FIELDS = (
    "materials",
    "constructions",
    "construction_sets",
    "schedule_type_limits",
    "schedules",
    "program_types",
    "hvacs",
    "shws",
)
_RADIANCE_MODEL_LIST_FIELDS = ("modifiers", "modifier_sets")


def get_dragonfly_properties_summary(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Read compact Dragonfly Energy/Radiance extension properties from a Garden."""
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_dragonfly_model(garden_root_path, resolved_model_target)

    buildings = []
    stories = []
    room2ds = []
    for building in model.buildings:
        buildings.append(_host_summary(building))
        for story in building.unique_stories:
            stories.append(
                _host_summary(
                    story,
                    parent={"building_identifier": building.identifier},
                )
            )
            for room in story.room_2ds:
                room2ds.append(
                    _host_summary(
                        room,
                        parent={
                            "building_identifier": building.identifier,
                            "story_identifier": story.identifier,
                        },
                    )
                )

    summary_view = {
        "garden_target": manifest.target(),
        "model_target": resolved_model_target,
        "model": _host_summary(model),
        "buildings": buildings,
        "stories": stories,
        "room2ds": room2ds,
        "counts": {
            "buildings": len(buildings),
            "stories": len(stories),
            "room2ds": len(room2ds),
        },
    }
    return {
        "model_target": resolved_model_target,
        "summary_view": summary_view,
        "report": make_report(
            status="ok",
            message=f"Read Dragonfly properties summary: {model.identifier}",
        ),
    }


def apply_dragonfly_energy_properties(
    *,
    garden_root: str,
    host_target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    program_type_identifier: str | None = None,
    construction_set_identifier: str | None = None,
) -> dict[str, Any]:
    """Apply narrow SDK-backed Dragonfly Energy properties to an object host."""
    updated_fields: list[str] = []
    if program_type_identifier is not None:
        updated_fields.append("program_type")
    if construction_set_identifier is not None:
        updated_fields.append("construction_set")
    if not updated_fields:
        raise ValueError(
            "apply_dragonfly_energy_properties requires at least one supported "
            "Energy property input."
        )

    normalized_target = normalize_dragonfly_object_target(host_target)
    host_type = normalized_target["object_type"]
    if host_type not in {"room2d", "story", "building"}:
        raise ValueError(
            "apply_dragonfly_energy_properties supports room2d, story, and "
            "building targets."
        )
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    host = _host_from_target(model, normalized_target)

    program_type = (
        program_type_by_identifier(program_type_identifier)
        if program_type_identifier is not None
        else None
    )
    construction_set = (
        construction_set_by_identifier(construction_set_identifier)
        if construction_set_identifier is not None
        else None
    )
    affected_room2d_count = 0
    if host_type == "room2d":
        if program_type is not None:
            host.properties.energy.program_type = program_type
            affected_room2d_count = 1
        if construction_set is not None:
            host.properties.energy.construction_set = construction_set
    elif host_type == "story":
        if program_type is not None:
            host.properties.energy.set_all_room_2d_program_type(program_type)
            affected_room2d_count = len(host.room_2ds)
        if construction_set is not None:
            host.properties.energy.construction_set = construction_set
    elif host_type == "building":
        if program_type is not None:
            host.properties.energy.set_all_room_2d_program_type(program_type)
            affected_room2d_count = len(host.unique_room_2ds)
        if construction_set is not None:
            host.properties.energy.construction_set = construction_set

    updated_model_target, persisted_path = save_dragonfly_model(
        garden_root_path,
        manifest,
        model,
        name=str(resolved_model_target["model_identifier"]),
        included_prop=["energy", "radiance", "uwg"],
        set_base=manifest.base_dragonfly_model == resolved_model_target,
    )
    summary_view = {
        "target": normalized_target,
        "model_target": updated_model_target,
        "host_type": host_type,
        "identifier": normalized_target["object_identifier"],
        "updated_fields": updated_fields,
        "program_type_identifier": program_type_identifier,
        "construction_set_identifier": construction_set_identifier,
        "affected_room2d_count": affected_room2d_count,
    }
    return {
        "target": normalized_target,
        "host_target": normalized_target,
        "model_target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "apply_dragonfly_energy_properties",
                "target": normalized_target,
                "updated_fields": updated_fields,
                "affected_room2d_count": affected_room2d_count,
            },
        ),
        "report": make_report(
            status="ok",
            message=(
                "Applied Dragonfly Energy properties to "
                f"{host_type}: {normalized_target['object_identifier']}"
            ),
        ),
    }


def apply_dragonfly_radiance_properties(
    *,
    garden_root: str,
    host_target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    modifier_set_identifier: str | None = None,
    grid_parameter_type: str | None = None,
    grid_dimension: float | None = None,
    grid_offset: float | None = None,
    wall_offset: float = 0,
    face_type: str = "Wall",
    aperture_type: str = "All",
    punched_geometry: bool = False,
    dir_count: int = 8,
    start_vector: list[float] | None = None,
    mesh_radius: float | None = None,
    include_mesh: bool = True,
    remove_existing_grid_parameters: bool = False,
) -> dict[str, Any]:
    """Apply narrow SDK-backed Dragonfly Radiance properties to an object host."""
    updated_fields: list[str] = []
    if modifier_set_identifier is not None:
        updated_fields.append("modifier_set")
    if grid_parameter_type is not None:
        updated_fields.append("grid_parameter")
    if remove_existing_grid_parameters:
        updated_fields.append("remove_existing_grid_parameters")
    if not updated_fields:
        raise ValueError(
            "apply_dragonfly_radiance_properties requires at least one supported "
            "Radiance property input."
        )

    normalized_target = normalize_dragonfly_object_target(host_target)
    host_type = normalized_target["object_type"]
    if host_type not in {"room2d", "story", "building"}:
        raise ValueError(
            "apply_dragonfly_radiance_properties supports room2d, story, and "
            "building targets."
        )
    if (grid_parameter_type is not None or remove_existing_grid_parameters) and (
        host_type not in {"room2d", "building"}
    ):
        raise ValueError(
            "Dragonfly Radiance grid parameters can be applied to room2d or "
            "building targets, not story targets."
        )

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    host = _host_from_target(model, normalized_target)

    modifier_set = (
        modifier_set_by_identifier(modifier_set_identifier)
        if modifier_set_identifier is not None
        else None
    )
    grid_parameter = _grid_parameter_from_input(
        grid_parameter_type=grid_parameter_type,
        grid_dimension=grid_dimension,
        grid_offset=grid_offset,
        wall_offset=wall_offset,
        face_type=face_type,
        aperture_type=aperture_type,
        punched_geometry=punched_geometry,
        dir_count=dir_count,
        start_vector=start_vector,
        mesh_radius=mesh_radius,
        include_mesh=include_mesh,
    )

    affected_room2d_count = 0
    if modifier_set is not None:
        host.properties.radiance.modifier_set = modifier_set
    if remove_existing_grid_parameters:
        if host_type == "room2d":
            host.properties.radiance.remove_grid_parameters()
            affected_room2d_count = 1
        elif host_type == "building":
            for room in host.unique_room_2ds:
                room.properties.radiance.remove_grid_parameters()
            affected_room2d_count = len(host.unique_room_2ds)
    if grid_parameter is not None:
        host.properties.radiance.add_grid_parameter(grid_parameter)
        affected_room2d_count = 1 if host_type == "room2d" else len(host.unique_room_2ds)

    updated_model_target, persisted_path = save_dragonfly_model(
        garden_root_path,
        manifest,
        model,
        name=str(resolved_model_target["model_identifier"]),
        included_prop=["energy", "radiance", "uwg"],
        set_base=manifest.base_dragonfly_model == resolved_model_target,
    )
    summary_view = {
        "target": normalized_target,
        "model_target": updated_model_target,
        "host_type": host_type,
        "identifier": normalized_target["object_identifier"],
        "updated_fields": updated_fields,
        "modifier_set_identifier": modifier_set_identifier,
        "grid_parameter": grid_parameter.to_dict() if grid_parameter is not None else None,
        "remove_existing_grid_parameters": remove_existing_grid_parameters,
        "affected_room2d_count": affected_room2d_count,
    }
    return {
        "target": normalized_target,
        "host_target": normalized_target,
        "model_target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "apply_dragonfly_radiance_properties",
                "target": normalized_target,
                "updated_fields": updated_fields,
                "affected_room2d_count": affected_room2d_count,
            },
        ),
        "report": make_report(
            status="ok",
            message=(
                "Applied Dragonfly Radiance properties to "
                f"{host_type}: {normalized_target['object_identifier']}"
            ),
        ),
    }

def _host_summary(host: Any, parent: dict[str, str] | None = None) -> dict[str, Any]:
    summary = {
        "identifier": getattr(host, "identifier", None),
        "display_name": getattr(host, "display_name", None),
        "type": host.__class__.__name__,
        "energy": _property_summary(host, "energy"),
        "radiance": _property_summary(host, "radiance"),
    }
    if parent:
        summary["parent"] = parent
    return summary


def _host_from_target(model: Any, target: dict[str, Any]) -> Any:
    object_type = target["object_type"]
    identifier = target["object_identifier"]
    if object_type == "room2d":
        return _one_by_identifier(
            model.room_2ds_by_identifier([identifier]),
            identifier,
            "Room2D",
        )
    if object_type == "story":
        return _one_by_identifier(
            model.stories_by_identifier([identifier]),
            identifier,
            "Story",
        )
    if object_type == "building":
        return _one_by_identifier(
            model.buildings_by_identifier([identifier]),
            identifier,
            "Building",
        )
    raise ValueError(f"Unsupported Dragonfly Energy host type: {object_type}.")


def _one_by_identifier(objects: list[Any], identifier: str, object_type: str) -> Any:
    if len(objects) == 1:
        return objects[0]
    if not objects:
        raise ValueError(f"Dragonfly {object_type} not found: {identifier}.")
    raise ValueError(f"Dragonfly {object_type} identifier is ambiguous: {identifier}.")


def _grid_parameter_from_input(
    *,
    grid_parameter_type: str | None,
    grid_dimension: float | None,
    grid_offset: float | None,
    wall_offset: float,
    face_type: str,
    aperture_type: str,
    punched_geometry: bool,
    dir_count: int,
    start_vector: list[float] | None,
    mesh_radius: float | None,
    include_mesh: bool,
) -> Any:
    if grid_parameter_type is None:
        return None
    if grid_dimension is None:
        raise ValueError("grid_dimension is required when grid_parameter_type is provided.")
    normalized_type = grid_parameter_type.strip().lower()
    offset = 1.0 if grid_offset is None else grid_offset
    if normalized_type == "room_grid":
        return RoomGridParameter(
            grid_dimension,
            offset=offset,
            wall_offset=wall_offset,
            include_mesh=include_mesh,
        )
    if normalized_type == "room_radial_grid":
        vector = (
            Vector3D(*start_vector)
            if start_vector is not None
            else Vector3D(0, -1, 0)
        )
        return RoomRadialGridParameter(
            grid_dimension,
            offset=1.2 if grid_offset is None else grid_offset,
            wall_offset=wall_offset,
            dir_count=dir_count,
            start_vector=vector,
            mesh_radius=mesh_radius,
            include_mesh=include_mesh,
        )
    if normalized_type == "exterior_face_grid":
        return ExteriorFaceGridParameter(
            grid_dimension,
            offset=0.1 if grid_offset is None else grid_offset,
            face_type=face_type,
            punched_geometry=punched_geometry,
            include_mesh=include_mesh,
        )
    if normalized_type == "exterior_aperture_grid":
        return ExteriorApertureGridParameter(
            grid_dimension,
            offset=0.1 if grid_offset is None else grid_offset,
            aperture_type=aperture_type,
            include_mesh=include_mesh,
        )
    raise ValueError(
        "grid_parameter_type must be room_grid, room_radial_grid, "
        "exterior_face_grid, or exterior_aperture_grid."
    )


def _property_summary(host: Any, extension: str) -> dict[str, Any]:
    properties = getattr(host, "properties", None)
    extension_properties = getattr(properties, extension, None)
    if extension_properties is None:
        return {"available": False, "to_dict_available": False}
    summary: dict[str, Any] = {
        "available": True,
        "type": extension_properties.__class__.__name__,
        "to_dict_available": hasattr(extension_properties, "to_dict"),
    }
    if not summary["to_dict_available"]:
        return summary
    try:
        data = extension_properties.to_dict()
    except Exception as exc:  # pragma: no cover - SDK defensive boundary
        summary["to_dict_error"] = str(exc)
        return summary
    extension_data = data.get(extension) if isinstance(data, dict) else None
    if not isinstance(extension_data, dict):
        return summary
    fields = _compact_fields(extension_data)
    if fields:
        summary["fields"] = fields
    object_counts = _model_object_counts(extension, extension_data)
    if object_counts:
        summary["object_counts"] = object_counts
    return summary


def _compact_fields(data: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for key in (
        "program_type",
        "construction_set",
        "hvac",
        "shw",
        "modifier_set",
        "ceiling_plenum_construction",
        "floor_plenum_construction",
    ):
        value = data.get(key)
        identifier = _identifier(value)
        if identifier is not None:
            fields[key] = identifier
    if isinstance(data.get("grid_parameters"), list):
        fields["grid_parameters"] = [
            _compact_grid_parameter(item)
            for item in data["grid_parameters"]
            if isinstance(item, dict)
        ]
    if data.get("has_des_loads") is not None:
        fields["has_des_loads"] = bool(data["has_des_loads"])
    return fields


def _identifier(value: Any) -> str | None:
    if isinstance(value, dict):
        identifier = value.get("identifier")
        return str(identifier) if identifier else None
    identifier = getattr(value, "identifier", None)
    return str(identifier) if identifier else None


def _compact_grid_parameter(value: dict[str, Any]) -> dict[str, Any]:
    keep = ("type", "dimension", "offset", "wall_offset", "face_type", "aperture_type")
    return {key: value[key] for key in keep if key in value}


def _model_object_counts(extension: str, data: dict[str, Any]) -> dict[str, int]:
    fields = (
        _ENERGY_MODEL_LIST_FIELDS
        if extension == "energy"
        else _RADIANCE_MODEL_LIST_FIELDS
    )
    return {
        field: len(data[field])
        for field in fields
        if isinstance(data.get(field), list)
    }
