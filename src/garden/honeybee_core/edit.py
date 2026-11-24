"""Honeybee object edit services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.altnumber import autosize
from honeybee.aperture import Aperture
from honeybee.boundarycondition import (
    Adiabatic,
    Ground,
    OtherSideTemperature,
    Outdoors,
    Surface,
    boundary_conditions,
)
from honeybee.door import Door
from honeybee.face import Face
from honeybee.facetype import face_types
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade
from honeybee_energy.construction.air import AirBoundaryConstruction
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.dictutil import dict_to_object
from honeybee_energy.construction.dictutil import dict_to_construction
from honeybee_energy.generator.loadcenter import ElectricLoadCenter
from honeybee_energy.generator.pv import PVProperties
from honeybee_energy.hvac import HVAC_TYPES_DICT
from honeybee_energy.hvac._base import _HVACSystem
from honeybee_energy.internalmass import InternalMass
from honeybee_energy.lib.constructions import (
    air_boundary as default_air_boundary_construction,
    opaque_construction_by_identifier,
    shade_construction_by_identifier,
    window_construction_by_identifier,
)
from honeybee_energy.lib.constructionsets import construction_set_by_identifier
from honeybee_energy.lib.programtypes import program_type_by_identifier
from honeybee_energy.lib.schedules import schedule_by_identifier
from honeybee_energy.load.daylight import DaylightingControl
from honeybee_energy.load.equipment import ElectricEquipment, GasEquipment
from honeybee_energy.load.hotwater import ServiceHotWater
from honeybee_energy.load.infiltration import Infiltration
from honeybee_energy.load.lighting import Lighting
from honeybee_energy.load.people import People
from honeybee_energy.load.process import Process
from honeybee_energy.load.setpoint import Setpoint
from honeybee_energy.load.ventilation import Ventilation
from honeybee_energy.programtype import ProgramType
from honeybee_energy.schedule.dictutil import dict_to_schedule
from honeybee_energy.shw import SHWSystem
from honeybee_energy.ventcool.control import VentilationControl
from honeybee_energy.ventcool.crack import AFNCrack
from honeybee_energy.ventcool.fan import VentilationFan
from honeybee_energy.ventcool.opening import VentilationOpening
from honeybee_radiance.dynamic.state import RadianceShadeState, RadianceSubFaceState
from honeybee_radiance.lib.modifiers import modifier_by_identifier
from honeybee_radiance.lib.modifiersets import modifier_set_by_identifier
from honeybee_radiance.modifier.modifierbase import Modifier
from honeybee_radiance.modifierset import ModifierSet
from honeybee_radiance.mutil import dict_to_modifier
from ladybug_geometry.geometry3d.pointvector import Point3D

try:
    from honeybee_energy.load.exhaust import ExhaustAir
except ImportError:  # pragma: no cover - honeybee-energy < 1.125
    ExhaustAir = None  # type: ignore[assignment,misc]

from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report
from garden.honeybee_core.geometry import (
    face3d_from_dict,
    validate_face_sub_faces,
    validate_honeybee_aperture,
    validate_honeybee_face,
    validate_honeybee_door,
    validate_honeybee_room,
    validate_honeybee_shade,
    validate_model_adjacency,
)
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_additions import (
    add_objects_to_model,
    remove_objects_from_model,
)
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
)
from garden.honeybee_core.postprocess import (
    apply_honeybee_postprocess,
    attach_postprocess_result,
)
from garden.honeybee_core.relate import _project_subface_to_face
from garden.honeybee_core.targets import (
    make_honeybee_object_target,
    normalize_honeybee_model_target,
    normalize_honeybee_object_target,
    object_summary,
)
from garden.libraries.properties import get_garden_properties_library_object


def _edit_response(
    *,
    manifest: Any,
    updated_model_target: dict[str, Any],
    persisted_path: str,
    operation: str,
    target: dict[str, Any],
    object_dict: dict[str, Any],
    updated_fields: list[str],
    postprocess: dict[str, Any] | None = None,
) -> dict[str, Any]:
    summary_view = object_summary(target, object_dict)
    summary_view["updated_fields"] = updated_fields
    return attach_postprocess_result({
        "object_dict": object_dict,
        "target": target,
        "summary_view": summary_view,
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": operation,
                "target": target,
                "updated_fields": updated_fields,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Edited Honeybee {target['object_type']}: {target['object_identifier']}",
        ),
    }, postprocess or {})


def _model_edit_response(
    *,
    manifest: Any,
    updated_model_target: dict[str, Any],
    persisted_path: str,
    object_dict: dict[str, Any],
    updated_fields: list[str],
    add_summary: dict[str, Any] | None = None,
    remove_summary: dict[str, Any] | None = None,
    postprocess: dict[str, Any] | None = None,
) -> dict[str, Any]:
    add_summary = add_summary or {
        "added_object_count": 0,
        "added_object_types": [],
    }
    remove_summary = remove_summary or {
        "removed_object_count": 0,
        "removed_object_types": [],
    }
    summary_view = {
        "target": updated_model_target,
        "identifier": object_dict.get("identifier"),
        "display_name": object_dict.get("display_name"),
        "type": object_dict.get("type"),
        "updated_fields": updated_fields,
        **add_summary,
        **remove_summary,
    }
    return attach_postprocess_result({
        "object_dict": updated_model_target,
        "target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": "edit_honeybee_model",
                "target": updated_model_target,
                "updated_fields": updated_fields,
                **add_summary,
                **remove_summary,
            },
        ),
        "report": make_report(
            status="ok",
            message=f"Edited Honeybee model: {updated_model_target['model_identifier']}",
        ),
    }, postprocess or {})


def _save_changed_model(
    *,
    garden_root: Path,
    manifest: Any,
    model_target: dict[str, Any],
    model: Model,
) -> tuple[dict[str, Any], str]:
    return save_honeybee_model(
        garden_root,
        manifest,
        model,
        name=str(model_target["model_identifier"]),
        set_base=manifest.base_honeybee_model == model_target,
    )


def _require_edit(updated_fields: list[str], object_type: str) -> None:
    if not updated_fields:
        raise ValueError(
            f"edit_honeybee_{object_type} requires at least one supported edit input."
        )


def _ensure_supported_surface_edit(
    *,
    obj: Aperture | Door,
    geometry_changed: bool,
    state_changed: bool,
    state_label: str,
    allow_geometry_update: bool = False,
) -> None:
    if not isinstance(obj.boundary_condition, Surface):
        return
    if geometry_changed and not allow_geometry_update:
        raise ValueError(
            f"Surface-adjacent Honeybee {obj.__class__.__name__} geometry updates are "
            "not supported yet because paired updates would be required."
        )
    if state_changed:
        raise ValueError(
            f"Surface-adjacent Honeybee {obj.__class__.__name__} updates cannot change "
            f"{state_label} independently because paired sub-faces must stay aligned."
        )


def _replace_hosted_shade(host: Any, original: Shade, edited: Shade) -> None:
    edited._parent = host
    edited._is_detached = False
    if original.is_indoor:
        edited._is_indoor = True
        host._indoor_shades = _replace_by_identifier(
            host._indoor_shades,
            original.identifier,
            edited,
        )
    else:
        edited._is_indoor = False
        host._outdoor_shades = _replace_by_identifier(
            host._outdoor_shades,
            original.identifier,
            edited,
        )
    original._parent = None


def _replace_hosted_subface(
    host: Face,
    original: Aperture | Door,
    edited: Aperture | Door,
    *,
    list_name: str,
    add_method_name: str,
) -> None:
    current = getattr(host, list_name)
    setattr(host, list_name, Model._remove_by_ids(current, [original.identifier]))
    host._punched_geometry = None
    original._parent = None
    getattr(host, add_method_name)(edited)


def _remove_hosted_subface(
    host: Face,
    original: Aperture | Door,
    *,
    list_name: str,
) -> None:
    current = getattr(host, list_name)
    setattr(host, list_name, Model._remove_by_ids(current, [original.identifier]))
    host._punched_geometry = None
    original._parent = None


def _surface_adjacent_door(model: Model, door: Door) -> Door:
    boundary_condition = door.boundary_condition
    if not isinstance(boundary_condition, Surface):
        raise ValueError("Door is not Surface-adjacent.")
    adjacent_door_id, adjacent_face_id, adjacent_room_id = (
        boundary_condition.boundary_condition_objects
    )
    for room in model.rooms:
        if room.identifier != adjacent_room_id:
            continue
        for face in room.faces:
            if face.identifier != adjacent_face_id:
                continue
            for candidate in face.doors:
                if candidate.identifier == adjacent_door_id:
                    return candidate
    raise ValueError(
        "The Surface-adjacent Honeybee Door pair could not be found: "
        f"{adjacent_door_id} on {adjacent_face_id} in {adjacent_room_id}."
    )


def _edit_surface_door_pair_geometry(
    model: Model,
    door: Door,
    *,
    geometry: dict[str, Any],
    display_name: str | None,
    user_data: dict[str, Any] | None,
    is_glass: bool | None,
) -> Door:
    host = door.parent
    if not isinstance(host, Face):
        raise ValueError("Surface-adjacent door parent must be a Honeybee Face.")
    adjacent_door = _surface_adjacent_door(model, door)
    adjacent_host = adjacent_door.parent
    if not isinstance(adjacent_host, Face):
        raise ValueError("Adjacent door parent must be a Honeybee Face.")

    edited_door = _edited_subface_from_geometry(
        door,
        geometry=geometry,
        display_name=display_name,
        user_data=user_data,
        state_field="is_glass",
        state_value=is_glass,
    )
    adjacent_edited = edited_door.duplicate()
    adjacent_edited.identifier = adjacent_door.identifier
    adjacent_edited.display_name = adjacent_door.display_name
    adjacent_edited.user_data = adjacent_door.user_data

    host.boundary_condition = boundary_conditions.outdoors
    adjacent_host.boundary_condition = boundary_conditions.outdoors
    _remove_hosted_subface(host, door, list_name="_doors")
    _remove_hosted_subface(adjacent_host, adjacent_door, list_name="_doors")
    host.add_door(edited_door)
    if not _project_subface_to_face(
        adjacent_edited,
        host,
        adjacent_host,
        tolerance=model.tolerance,
        angle_tolerance=model.angle_tolerance,
    ):
        raise ValueError(
            "Could not project the edited Surface-adjacent Honeybee Door "
            f"geometry onto the paired face: {adjacent_host.identifier}."
        )
    validate_face_sub_faces(host)
    validate_face_sub_faces(adjacent_host)
    host.set_adjacency(adjacent_host, tolerance=model.tolerance)
    validate_model_adjacency(model)
    return edited_door


def _replace_by_identifier(objects: list[Any], identifier: str, replacement: Any) -> list[Any]:
    replaced = False
    new_objects: list[Any] = []
    for obj in objects:
        if obj.identifier == identifier:
            new_objects.append(replacement)
            replaced = True
        else:
            new_objects.append(obj)
    if not replaced:
        raise ValueError(f"Honeybee object not found for replacement: {identifier}")
    return new_objects


def _edited_shade_from_geometry(
    shade: Shade,
    *,
    geometry: dict[str, Any],
    display_name: str | None,
    user_data: dict[str, Any] | None,
    is_detached: bool | None,
) -> Shade:
    face3d_from_dict(geometry)
    shade_dict = shade.to_dict()
    shade_dict["geometry"] = geometry
    if display_name is not None:
        shade_dict["display_name"] = display_name
    if user_data is not None:
        shade_dict["user_data"] = user_data
    if is_detached is not None:
        shade_dict["is_detached"] = is_detached
    edited = Shade.from_dict(shade_dict)
    validate_honeybee_shade(edited)
    return edited


def _edited_subface_from_geometry(
    obj: Aperture | Door,
    *,
    geometry: dict[str, Any],
    display_name: str | None,
    user_data: dict[str, Any] | None,
    state_field: str,
    state_value: bool | None,
) -> Aperture | Door:
    face3d_from_dict(geometry)
    obj_dict = obj.to_dict()
    obj_dict["geometry"] = geometry
    if display_name is not None:
        obj_dict["display_name"] = display_name
    if user_data is not None:
        obj_dict["user_data"] = user_data
    if state_value is not None:
        obj_dict[state_field] = state_value
    edited = obj.__class__.from_dict(obj_dict)
    if isinstance(edited, Aperture):
        validate_honeybee_aperture(edited)
    else:
        validate_honeybee_door(edited)
    return edited


def _modifier_from_input(data: dict[str, Any] | str) -> Modifier:
    try:
        if isinstance(data, str):
            return modifier_by_identifier(data)
        return dict_to_modifier(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Radiance modifier input. {exc}") from exc


def _construction_from_dict(data: dict[str, Any] | str) -> Any:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if isinstance(data, str):
        normalized = data.strip().lower().replace("_", " ")
        if normalized in {"air boundary", "airboundary", "generic air boundary"}:
            return default_air_boundary_construction
        for resolver in (
            opaque_construction_by_identifier,
            window_construction_by_identifier,
            shade_construction_by_identifier,
        ):
            try:
                return resolver(data)
            except Exception:
                continue
        raise ValueError(f"Honeybee Energy construction identifier not found: {data!r}.")
    try:
        return dict_to_construction(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy construction input. {exc}") from exc


def _validate_face_construction(face: Face, construction: Any) -> Any:
    if face.type == face_types.air_boundary:
        if not isinstance(construction, (OpaqueConstruction, AirBoundaryConstruction)):
            raise ValueError(
                "construction must resolve to a Honeybee OpaqueConstruction or "
                "AirBoundaryConstruction for AirBoundary faces."
            )
        return construction
    if not isinstance(construction, OpaqueConstruction):
        raise ValueError("construction must resolve to a Honeybee opaque construction.")
    return construction


def _schedule_from_dict(data: dict[str, Any] | str) -> Any:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if isinstance(data, str):
        try:
            return schedule_by_identifier(data)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(f"Invalid Honeybee Energy schedule identifier. {exc}") from exc
    try:
        return dict_to_schedule(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy schedule input. {exc}") from exc


def _face_type_from_input(data: str | dict[str, Any]) -> Any:
    type_name = data.get("type") if isinstance(data, dict) else data
    if not isinstance(type_name, str) or not type_name.strip():
        raise ValueError("type must be a Honeybee Face type name or dict.")
    normalized = type_name.replace("_", "").replace(" ", "").lower()
    try:
        return face_types.by_name(normalized)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Face type input. {exc}") from exc


def _boundary_condition_from_input(data: str | dict[str, Any]) -> Any:
    if isinstance(data, dict):
        type_name = data.get("type")
        if not isinstance(type_name, str) or not type_name.strip():
            raise ValueError("boundary_condition dict must include a type field.")
        normalized = type_name.replace("_", "").replace(" ", "").lower()
        if normalized == "surface":
            raise ValueError(
                "Surface boundary condition updates are not supported in this edit slice."
            )
        try:
            if normalized == "outdoors":
                return Outdoors.from_dict(data)
            if normalized == "othersidetemperature":
                return OtherSideTemperature.from_dict(data)
            if normalized == "adiabatic":
                return Adiabatic.from_dict(data)
            if normalized == "ground":
                return Ground.from_dict(data)
            return boundary_conditions.by_name(normalized)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(f"Invalid Honeybee boundary condition input. {exc}") from exc

    normalized = data.replace("_", "").replace(" ", "").lower()
    if normalized == "surface":
        raise ValueError(
            "Surface boundary condition updates are not supported in this edit slice."
        )
    try:
        return boundary_conditions.by_name(normalized)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee boundary condition input. {exc}") from exc


def _vent_crack_from_dict(data: dict[str, Any]) -> AFNCrack:
    try:
        return AFNCrack.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy vent crack input. {exc}") from exc


def _construction_set_from_input(data: dict[str, Any] | str) -> ConstructionSet:
    try:
        if isinstance(data, str):
            return construction_set_by_identifier(data)
        return ConstructionSet.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy construction set input. {exc}") from exc


def _program_type_from_input(data: dict[str, Any] | str) -> ProgramType:
    try:
        if isinstance(data, str):
            return program_type_by_identifier(data)
        result = dict_to_object(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy program type input. {exc}") from exc
    if not isinstance(result, ProgramType):
        raise ValueError("program_type must resolve to a Honeybee ProgramType.")
    return result


def _library_object_dict_from_target(
    *,
    garden_root: Path,
    data: Any,
    field_name: str,
    domain: str,
    object_family: str | tuple[str, ...],
) -> Any:
    if isinstance(data, dict) and isinstance(data.get("target"), dict):
        data = data["target"]
    if not isinstance(data, dict) or data.get("target_type") != "garden_properties_library_object":
        return data
    allowed = (object_family,) if isinstance(object_family, str) else tuple(object_family)
    if data.get("domain") != domain or data.get("object_family") not in allowed:
        raise ValueError(
            f"{field_name} target must reference {domain}:{'/'.join(allowed)}."
        )
    return get_garden_properties_library_object(
        garden_root=str(garden_root),
        target=data,
    )["object_dict"]


def _hvac_from_dict(data: dict[str, Any]) -> _HVACSystem:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    hvac_type = data.get("type") if isinstance(data, dict) else None
    if not isinstance(hvac_type, str):
        raise ValueError(
            "hvac must be a Honeybee Energy HVAC dictionary with a type field."
        )
    hvac_cls = HVAC_TYPES_DICT.get(hvac_type)
    if hvac_cls is None:
        allowed = ", ".join(sorted(HVAC_TYPES_DICT))
        raise ValueError(
            f"Unsupported Honeybee Energy HVAC type: {hvac_type}. "
            f"Supported types: {allowed}."
        )
    try:
        result = hvac_cls.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy HVAC input. {exc}") from exc
    if not isinstance(result, _HVACSystem):
        raise ValueError("hvac must resolve to a Honeybee Energy HVAC object.")
    return result


def _ventilation_from_dict(data: dict[str, Any]) -> Ventilation:
    try:
        result = dict_to_object(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy ventilation input. {exc}") from exc
    if not isinstance(result, Ventilation):
        raise ValueError("ventilation must resolve to a Honeybee Ventilation object.")
    return result


def _setpoint_from_dict(data: dict[str, Any]) -> Setpoint:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    try:
        result = dict_to_object(data)
    except Exception:
        result = _setpoint_from_serialized_dict(data)
    if not isinstance(result, Setpoint):
        raise ValueError("setpoint must resolve to a Honeybee Setpoint object.")
    return result


def _electric_load_center_from_dict(data: dict[str, Any]) -> ElectricLoadCenter:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    try:
        return ElectricLoadCenter.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy electric load center input. {exc}") from exc


def _zone_ventilation_fan_from_dict(data: dict[str, Any]) -> VentilationFan:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    try:
        return VentilationFan.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy zone ventilation fan input. {exc}") from exc


def _parse_collection_update(
    data: Any,
    *,
    field_name: str,
    item_type: str,
    collection_keys: tuple[str, ...],
) -> tuple[str, list[Any]]:
    if isinstance(data, list):
        return "replace_all", data
    if not isinstance(data, dict):
        return "replace_all", [data]
    if isinstance(data.get("target"), dict) and data["target"].get("target_type") == "garden_properties_library_object":
        return "replace_all", [data]
    if data.get("target_type") == "garden_properties_library_object" or data.get("type") == item_type:
        return "replace_all", [data]
    if "operation" not in data and not any(key in data for key in collection_keys):
        return "replace_all", [data]

    operation = str(data.get("operation", "replace_all"))
    if operation not in {"replace_all", "add", "clear"}:
        raise ValueError(
            f"{field_name}.operation must be replace_all, add, or clear."
        )
    if operation == "clear":
        return operation, []
    items = None
    for key in collection_keys:
        if key in data:
            items = data[key]
            break
    if items is None:
        items = []
    if not isinstance(items, list):
        raise ValueError(f"{field_name} collection must be a list.")
    return operation, items


def _parse_zone_ventilation_fan_update(data: Any) -> tuple[str, list[Any]]:
    return _parse_collection_update(
        data,
        field_name="zone_ventilation_fans",
        item_type="VentilationFan",
        collection_keys=("fans", "zone_ventilation_fans"),
    )


def _parse_process_loads_update(data: Any) -> tuple[str, list[Any]]:
    return _parse_collection_update(
        data,
        field_name="process_loads",
        item_type="Process",
        collection_keys=("process_loads", "processes", "items"),
    )


def _parse_internal_masses_update(data: Any) -> tuple[str, list[Any]]:
    return _parse_collection_update(
        data,
        field_name="internal_masses",
        item_type="InternalMass",
        collection_keys=("internal_masses", "masses", "items"),
    )


def _resolve_schedule_value(data: Any, *, field_name: str, garden_root: Path | None = None) -> Any:
    if data is None:
        return None
    if garden_root is not None:
        data = _library_object_dict_from_target(
            garden_root=garden_root,
            data=data,
            field_name=field_name,
            domain="honeybee_energy",
            object_family="schedule",
        )
    return _schedule_from_serialized_setpoint(data, field_name=field_name)


def _room_load_from_input(
    data: Any,
    load_cls: Any,
    *,
    field_name: str,
    garden_root: Path | None = None,
) -> Any:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if garden_root is not None:
        data = _library_object_dict_from_target(
            garden_root=garden_root,
            data=data,
            field_name=field_name,
            domain="honeybee_energy",
            object_family="load",
        )
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a {load_cls.__name__} dict or Garden target.")
    if data.get("type") == load_cls.__name__:
        cleaned = dict(data)
        for sched_key in ("schedule", "occupancy_schedule", "activity_schedule"):
            if sched_key in cleaned and cleaned[sched_key] is not None and not isinstance(cleaned[sched_key], dict):
                cleaned[sched_key] = _resolve_schedule_value(
                    cleaned[sched_key],
                    field_name=f"{field_name}.{sched_key}",
                    garden_root=garden_root,
                ).to_dict()
        data = cleaned
    from garden.energy.programtypes import _load_from_input

    return _load_from_input(
        data,
        load_cls,
        field_name=field_name,
        garden_root=str(garden_root) if garden_root is not None else None,
    )


def _exhaust_from_input(data: Any, *, garden_root: Path | None = None) -> Any:
    if ExhaustAir is None:
        raise ValueError(
            "Room exhaust override requires honeybee-energy>=1.125 (ExhaustAir); "
            "in honeybee-energy 1.124.5 use zone_ventilation_fans with ventilation_type='Exhaust'."
        )
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if garden_root is not None:
        data = _library_object_dict_from_target(
            garden_root=garden_root,
            data=data,
            field_name="exhaust",
            domain="honeybee_energy",
            object_family=("exhaust_air", "load"),
        )
    if not isinstance(data, dict):
        raise ValueError("exhaust must be an ExhaustAir dict or Garden target.")
    if data.get("type") == "ExhaustAir":
        return ExhaustAir.from_dict(data)
    identifier = str(data.get("identifier") or "custom_exhaust")
    sched = _resolve_schedule_value(data.get("schedule"), field_name="exhaust.schedule", garden_root=garden_root)
    bal_sched = _resolve_schedule_value(
        data.get("balancing_schedule"),
        field_name="exhaust.balancing_schedule",
        garden_root=garden_root,
    )
    return ExhaustAir(
        identifier,
        flow_per_area=float(data.get("flow_per_area") or 0),
        flow_per_fixture=float(data.get("flow_per_fixture") or 0),
        fixture_count=int(data.get("fixture_count") or 1),
        schedule=sched,
        pressure_rise=float(data.get("pressure_rise", 125)),
        efficiency=float(data.get("efficiency", 0.35)),
        balancing_schedule=bal_sched,
    )


def _process_from_input(data: Any, *, garden_root: Path | None = None) -> Process:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if garden_root is not None:
        data = _library_object_dict_from_target(
            garden_root=garden_root,
            data=data,
            field_name="process_loads",
            domain="honeybee_energy",
            object_family=("process", "load"),
        )
    if not isinstance(data, dict):
        raise ValueError("process_loads items must be Process dicts or Garden targets.")
    if data.get("type") == "Process":
        cleaned = dict(data)
        if cleaned.get("schedule") is not None and not isinstance(cleaned["schedule"], dict):
            cleaned["schedule"] = _resolve_schedule_value(
                cleaned["schedule"],
                field_name="process_loads.schedule",
                garden_root=garden_root,
            ).to_dict()
        try:
            return Process.from_dict(cleaned)
        except Exception as exc:
            raise ValueError(f"Invalid Process input. {exc}") from exc
    if data.get("watts") is None:
        raise ValueError("Process shorthand requires 'watts'.")
    identifier = str(data.get("identifier") or "custom_process")
    sched = _resolve_schedule_value(
        data.get("schedule"),
        field_name="process_loads.schedule",
        garden_root=garden_root,
    )
    try:
        return Process(
            identifier,
            float(data["watts"]),
            schedule=sched,
            fuel_type=str(data.get("fuel_type") or "Electricity"),
            end_use_category=str(data.get("end_use_category") or "Process"),
            radiant_fraction=float(data.get("radiant_fraction", 0)),
            latent_fraction=float(data.get("latent_fraction", 0)),
            lost_fraction=float(data.get("lost_fraction", 0)),
        )
    except Exception as exc:
        raise ValueError(f"Invalid Process shorthand input. {exc}") from exc


def _internal_mass_from_input(data: Any, *, garden_root: Path | None = None) -> InternalMass:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if garden_root is not None:
        data = _library_object_dict_from_target(
            garden_root=garden_root,
            data=data,
            field_name="internal_masses",
            domain="honeybee_energy",
            object_family=("internal_mass", "load"),
        )
    if not isinstance(data, dict):
        raise ValueError("internal_masses items must be InternalMass dicts or Garden targets.")
    constr_raw = data.get("construction")
    if constr_raw is None:
        raise ValueError("InternalMass requires a 'construction'.")
    if garden_root is not None:
        constr_raw = _library_object_dict_from_target(
            garden_root=garden_root,
            data=constr_raw,
            field_name="internal_masses.construction",
            domain="honeybee_energy",
            object_family="construction",
        )
    constr = _construction_from_dict(constr_raw)
    if not isinstance(constr, OpaqueConstruction):
        raise ValueError("InternalMass construction must be an OpaqueConstruction.")
    if data.get("area") is None:
        raise ValueError("InternalMass requires an 'area'.")
    identifier = str(data.get("identifier") or "custom_internal_mass")
    try:
        mass = InternalMass(identifier, constr, float(data["area"]))
        if data.get("display_name") is not None:
            mass.display_name = data["display_name"]
        if data.get("user_data") is not None:
            mass.user_data = dict(data["user_data"])
        return mass
    except Exception as exc:
        raise ValueError(f"Invalid InternalMass input. {exc}") from exc


def _shw_from_input(data: Any, *, garden_root: Path | None = None) -> SHWSystem:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if garden_root is not None:
        data = _library_object_dict_from_target(
            garden_root=garden_root,
            data=data,
            field_name="shw",
            domain="honeybee_energy",
            object_family=("shw_system", "hvac", "load"),
        )
    if not isinstance(data, dict):
        raise ValueError("shw must be an SHWSystem dict or Garden target.")
    if data.get("type") == "SHWSystem":
        try:
            return SHWSystem.from_dict(data)
        except Exception as exc:
            raise ValueError(f"Invalid SHWSystem input. {exc}") from exc
    identifier = str(data.get("identifier") or "custom_shw")
    eff = data.get("heater_efficiency", autosize)
    if isinstance(eff, str) and eff.strip().lower() == "autosize":
        eff = autosize
    elif isinstance(eff, dict) and eff.get("type") == "Autosize":
        eff = autosize
    elif eff is None:
        eff = autosize
    try:
        return SHWSystem(
            identifier,
            equipment_type=str(data.get("equipment_type") or "Gas_WaterHeater"),
            heater_efficiency=eff,
            ambient_condition=data.get("ambient_condition", 22),
            ambient_loss_coefficient=float(data.get("ambient_loss_coefficient", 6)),
        )
    except Exception as exc:
        raise ValueError(f"Invalid SHWSystem shorthand input. {exc}") from exc


def _window_vent_control_from_input(
    data: Any, *, garden_root: Path | None = None
) -> VentilationControl:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if not isinstance(data, dict):
        raise ValueError("window_vent_control must be a VentilationControl dictionary.")
    cleaned = dict(data)
    if "schedule" in cleaned and cleaned["schedule"] is not None:
        sched_obj = _resolve_schedule_value(
            cleaned["schedule"],
            field_name="window_vent_control.schedule",
            garden_root=garden_root,
        )
        cleaned["schedule"] = sched_obj.to_dict() if hasattr(sched_obj, "to_dict") else sched_obj
    if cleaned.get("type") == "VentilationControl":
        try:
            return VentilationControl.from_dict(cleaned)
        except Exception as exc:
            raise ValueError(f"Invalid VentilationControl input. {exc}") from exc
    try:
        sched = (
            dict_to_schedule(cleaned["schedule"])
            if cleaned.get("schedule") is not None
            else None
        )
        kwargs: dict[str, Any] = {
            "min_indoor_temperature": float(cleaned.get("min_indoor_temperature", -100)),
            "max_indoor_temperature": float(cleaned.get("max_indoor_temperature", 100)),
            "min_outdoor_temperature": float(cleaned.get("min_outdoor_temperature", -100)),
            "max_outdoor_temperature": float(cleaned.get("max_outdoor_temperature", 100)),
            "delta_temperature": float(cleaned.get("delta_temperature", -100)),
        }
        if sched is not None:
            kwargs["schedule"] = sched
        return VentilationControl(**kwargs)
    except Exception as exc:
        raise ValueError(f"Invalid window_vent_control shorthand input. {exc}") from exc


def _daylighting_control_from_input(data: Any) -> DaylightingControl:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        data = data["object_dict"]
    if not isinstance(data, dict):
        raise ValueError("daylighting_control must be a DaylightingControl dictionary.")
    if data.get("type") == "DaylightingControl":
        try:
            return DaylightingControl.from_dict(data)
        except Exception as exc:
            raise ValueError(f"Invalid DaylightingControl input. {exc}") from exc
    pos = data.get("sensor_position")
    if isinstance(pos, dict):
        sensor_pt = Point3D.from_dict(pos)
    elif isinstance(pos, (list, tuple)) and len(pos) == 3:
        sensor_pt = Point3D(float(pos[0]), float(pos[1]), float(pos[2]))
    else:
        raise ValueError(
            "daylighting_control requires sensor_position as [x, y, z] or Point3D dict."
        )
    try:
        return DaylightingControl(
            sensor_pt,
            illuminance_setpoint=float(data.get("illuminance_setpoint", 300)),
            control_fraction=float(data.get("control_fraction", 1)),
            min_power_input=float(data.get("min_power_input", 0.3)),
            min_light_output=float(data.get("min_light_output", 0.2)),
            off_at_minimum=bool(data.get("off_at_minimum", False)),
        )
    except Exception as exc:
        raise ValueError(f"Invalid daylighting_control shorthand input. {exc}") from exc


def _apply_make_plenum(room: Room, value: Any) -> None:
    if value is False:
        raise ValueError(
            "make_plenum=false is not reversible directly; use reset_fields or room loads instead."
        )
    if value is True:
        room.properties.energy.make_plenum()
        return
    if not isinstance(value, dict):
        raise ValueError("make_plenum must be true or an options dict.")
    allowed = {"conditioned", "remove_infiltration", "include_floor_area"}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(
            f"Unsupported make_plenum option(s): {', '.join(unknown)}. "
            f"Allowed: {', '.join(sorted(allowed))}."
        )
    room.properties.energy.make_plenum(
        conditioned=bool(value.get("conditioned", False)),
        remove_infiltration=bool(value.get("remove_infiltration", False)),
        include_floor_area=bool(value.get("include_floor_area", False)),
    )


def _apply_make_ground(room: Room, value: Any, *, garden_root: Path | None = None) -> None:
    include_floor_area = False
    constr_raw = value
    if isinstance(value, dict) and "soil_construction" in value:
        constr_raw = value["soil_construction"]
        include_floor_area = bool(value.get("include_floor_area", False))
    if garden_root is not None:
        constr_raw = _library_object_dict_from_target(
            garden_root=garden_root,
            data=constr_raw,
            field_name="make_ground",
            domain="honeybee_energy",
            object_family="construction",
        )
    constr = _construction_from_dict(constr_raw)
    if not isinstance(constr, OpaqueConstruction):
        raise ValueError("make_ground requires an OpaqueConstruction soil_construction.")
    room.properties.energy.make_ground(constr, include_floor_area=include_floor_area)


_ROOM_RESETTABLE_FIELDS = {
    "program_type",
    "construction_set",
    "hvac",
    "shw",
    "people",
    "lighting",
    "electric_equipment",
    "gas_equipment",
    "service_hot_water",
    "infiltration",
    "ventilation",
    "exhaust",
    "setpoint",
    "window_vent_control",
    "daylighting_control",
    "zone_ventilation_fans",
    "process_loads",
    "internal_masses",
    "loads",
    "modifier_set",
    "story",
    "zone",
}
_FACE_RESETTABLE_FIELDS = {"construction", "vent_crack", "modifier", "modifier_blk"}
_SUBFACE_RESETTABLE_FIELDS = {
    "construction",
    "vent_opening",
    "modifier",
    "modifier_blk",
    "dynamic_group_identifier",
    "states",
}
_SHADE_RESETTABLE_FIELDS = {
    "construction",
    "transmittance_schedule",
    "pv_properties",
    "modifier",
    "modifier_blk",
    "dynamic_group_identifier",
    "states",
}
_RESETTABLE_FIELDS_BY_TYPE = {
    "room": _ROOM_RESETTABLE_FIELDS,
    "face": _FACE_RESETTABLE_FIELDS,
    "aperture": _SUBFACE_RESETTABLE_FIELDS,
    "door": _SUBFACE_RESETTABLE_FIELDS,
    "shade": _SHADE_RESETTABLE_FIELDS,
}


def _validate_reset_fields(reset_fields: Any, *, object_type: str) -> list[str]:
    if not isinstance(reset_fields, list) or not reset_fields:
        raise ValueError("reset_fields must be a non-empty list of field name strings.")
    allowed = _RESETTABLE_FIELDS_BY_TYPE.get(object_type, set())
    cleaned: list[str] = []
    for index, raw in enumerate(reset_fields):
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError(f"reset_fields[{index}] must be a non-empty string.")
        field = raw.strip()
        if field not in allowed:
            raise ValueError(
                f"Field {field!r} cannot be reset on Honeybee {object_type}. "
                f"Supported reset_fields: {', '.join(sorted(allowed))}."
            )
        if field not in cleaned:
            cleaned.append(field)
    return cleaned


def _apply_room_reset_fields(room: Room, reset_fields: list[str]) -> bool:
    changed = False
    energy = room.properties.energy
    radiance = room.properties.radiance
    for field in reset_fields:
        if field == "loads":
            load_attrs = (
                "_people",
                "_lighting",
                "_electric_equipment",
                "_gas_equipment",
                "_service_hot_water",
                "_infiltration",
                "_ventilation",
                "_setpoint",
            )
            if any(getattr(energy, attr, None) is not None for attr in load_attrs):
                changed = True
            energy.reset_loads_to_program()
        elif field == "zone_ventilation_fans":
            if energy.fans:
                energy.remove_fans()
                changed = True
        elif field == "process_loads":
            if energy.process_loads:
                energy.remove_process_loads()
                changed = True
        elif field == "internal_masses":
            if energy.internal_masses:
                energy.remove_internal_masses()
                changed = True
        elif field == "modifier_set":
            if getattr(radiance, "_modifier_set", None) is not None:
                radiance.modifier_set = None
                changed = True
        elif field == "story":
            if room.story is not None:
                room.story = None
                changed = True
        elif field == "zone":
            if room.zone is not None:
                room.zone = None
                changed = True
        elif field == "exhaust":
            if hasattr(energy, "exhaust") and getattr(energy, "_exhaust", None) is not None:
                energy.exhaust = None
                changed = True
        else:
            if getattr(energy, f"_{field}", None) is not None:
                setattr(energy, field, None)
                changed = True
    return changed


def _apply_object_reset_fields(obj: Any, reset_fields: list[str]) -> None:
    energy = obj.properties.energy
    radiance = obj.properties.radiance
    for field in reset_fields:
        if field == "states":
            radiance.remove_states()
        elif field in {"modifier", "modifier_blk", "dynamic_group_identifier"}:
            setattr(radiance, field, None)
        else:
            setattr(energy, field, None)


def _apply_room_collection_update(
    *,
    desired: list[Any],
    operation: str,
    current_items: list[Any],
    remove_fn: Any,
    add_fn: Any,
    conflict_label: str,
) -> bool:
    if operation == "clear":
        if not current_items:
            return False
        remove_fn()
        return True
    if operation == "replace_all":
        if [_serialized_hb_obj(item) for item in current_items] == [
            _serialized_hb_obj(item) for item in desired
        ]:
            return False
        remove_fn()
        for item in desired:
            add_fn(_duplicate_hb_obj(item))
        return True
    existing_by_id = {str(item.identifier): item for item in current_items}
    pending: dict[str, Any] = {}
    for item in desired:
        identifier = str(item.identifier)
        existing = existing_by_id.get(identifier) or pending.get(identifier)
        if existing is not None:
            if _serialized_hb_obj(existing) != _serialized_hb_obj(item):
                raise ValueError(
                    f"{conflict_label}.add contains a conflicting identifier: {identifier}."
                )
            continue
        pending[identifier] = item
    for item in pending.values():
        add_fn(_duplicate_hb_obj(item))
    return bool(pending)


def _apply_room_fans_batch(energy: Any, operation: str, desired: list[Any]) -> bool:
    return _apply_room_collection_update(
        desired=desired,
        operation=operation,
        current_items=list(energy.fans or []),
        remove_fn=energy.remove_fans,
        add_fn=energy.add_fan,
        conflict_label="zone_ventilation_fans",
    )


def _apply_room_process_loads_batch(energy: Any, operation: str, desired: list[Any]) -> bool:
    return _apply_room_collection_update(
        desired=desired,
        operation=operation,
        current_items=list(energy.process_loads or []),
        remove_fn=energy.remove_process_loads,
        add_fn=energy.add_process_load,
        conflict_label="process_loads",
    )


def _apply_room_internal_masses_batch(energy: Any, operation: str, desired: list[Any]) -> bool:
    return _apply_room_collection_update(
        desired=desired,
        operation=operation,
        current_items=list(energy.internal_masses or []),
        remove_fn=energy.remove_internal_masses,
        add_fn=energy.add_internal_mass,
        conflict_label="internal_masses",
    )


def _schedule_from_serialized_setpoint(data: Any, *, field_name: str) -> Any:
    if data is None:
        return None
    if isinstance(data, str):
        try:
            return schedule_by_identifier(data)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(
                f"{field_name} schedule library identifier was not found. {exc}"
            ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a schedule dict or library identifier.")

    try:
        return dict_to_schedule(data)
    except Exception as dict_exc:
        identifier = data.get("identifier")
        if isinstance(identifier, str):
            try:
                return schedule_by_identifier(identifier)
            except Exception:
                pass
        raise ValueError(
            f"{field_name} must be a valid Honeybee Energy schedule. {dict_exc}"
        ) from dict_exc


def _setpoint_from_serialized_dict(data: dict[str, Any]) -> Setpoint:
    if not isinstance(data, dict) or data.get("type") != "Setpoint":
        raise ValueError("setpoint must be a Honeybee Energy Setpoint dictionary.")
    try:
        return Setpoint(
            data["identifier"],
            _schedule_from_serialized_setpoint(
                data.get("heating_schedule"),
                field_name="heating_schedule",
            ),
            _schedule_from_serialized_setpoint(
                data.get("cooling_schedule"),
                field_name="cooling_schedule",
            ),
            humidifying_schedule=_schedule_from_serialized_setpoint(
                data.get("humidifying_schedule"),
                field_name="humidifying_schedule",
            ),
            dehumidifying_schedule=_schedule_from_serialized_setpoint(
                data.get("dehumidifying_schedule"),
                field_name="dehumidifying_schedule",
            ),
            setpoint_cutout_difference=data.get("setpoint_cutout_difference", 0),
        )
    except Exception as exc:
        raise ValueError(f"Invalid Honeybee Energy setpoint input. {exc}") from exc


def _modifier_set_from_dict(data: dict[str, Any] | str) -> ModifierSet:
    try:
        if isinstance(data, str):
            return modifier_set_by_identifier(data)
        return ModifierSet.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Radiance modifier set input. {exc}") from exc


def _subface_state_from_dict(data: dict[str, Any]) -> RadianceSubFaceState:
    try:
        return RadianceSubFaceState.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Radiance sub-face state input. {exc}") from exc


def _shade_state_from_dict(data: dict[str, Any]) -> RadianceShadeState:
    try:
        return RadianceShadeState.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Radiance shade state input. {exc}") from exc


def _apply_energy_hot_swaps_to_shade(
    shade: Shade,
    *,
    construction: dict[str, Any] | None,
    transmittance_schedule: dict[str, Any] | None,
    pv_properties: dict[str, Any] | None,
) -> None:
    energy = shade.properties.energy
    if construction is not None:
        energy.construction = _construction_from_dict(construction)
    if transmittance_schedule is not None:
        energy.transmittance_schedule = _schedule_from_dict(transmittance_schedule)
    if pv_properties is not None:
        try:
            energy.pv_properties = PVProperties.from_dict(pv_properties)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(f"Invalid Honeybee Energy PV properties input. {exc}") from exc


def _apply_energy_hot_swaps_to_subface(
    obj: Aperture | Door,
    *,
    construction: dict[str, Any] | None,
    vent_opening: dict[str, Any] | None,
) -> None:
    energy = obj.properties.energy
    if construction is not None:
        energy.construction = _construction_from_dict(construction)
    if vent_opening is not None:
        try:
            energy.vent_opening = VentilationOpening.from_dict(vent_opening)
        except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
            raise ValueError(f"Invalid Honeybee Energy ventilation opening input. {exc}") from exc


def _parse_state_update(states: Any) -> tuple[str, list[dict[str, Any]]]:
    if states is None:
        return "none", []
    if isinstance(states, list):
        return "replace_all", states
    if not isinstance(states, dict):
        raise ValueError("states must be a list or a dict with operation metadata.")

    operation = str(states.get("operation", "replace_all"))
    states = states.get("states", [])
    if operation not in {"replace_all", "add", "clear"}:
        raise ValueError(
            "states.operation must be one of replace_all, add, or clear."
        )
    if operation == "clear":
        return operation, []
    if not isinstance(states, list):
        raise ValueError("states.states must be a list when provided.")
    return operation, states


def _apply_radiance_state_update(
    radiance: Any,
    *,
    operation: str,
    states: list[dict[str, Any]],
    state_loader,
) -> None:
    if operation == "none":
        return
    if operation == "clear":
        radiance.remove_states()
        return

    loaded_states = [state_loader(state) for state in states]
    if operation == "replace_all":
        radiance.remove_states()
        radiance.states = loaded_states
        return
    for state in loaded_states:
        radiance.add_state(state)


def _apply_radiance_hot_swaps(
    obj: Aperture | Door | Shade,
    *,
    modifier: dict[str, Any] | str | None,
    modifier_blk: dict[str, Any] | str | None,
    dynamic_group_identifier: str | None,
    states: Any,
    state_loader,
) -> None:
    radiance = obj.properties.radiance
    if modifier is not None:
        radiance.modifier = _modifier_from_input(modifier)
    if modifier_blk is not None:
        radiance.modifier_blk = _modifier_from_input(modifier_blk)
    if dynamic_group_identifier is not None:
        radiance.dynamic_group_identifier = dynamic_group_identifier

    operation, states = _parse_state_update(states)
    if operation in {"replace_all", "add"} and radiance.dynamic_group_identifier is None:
        raise ValueError(
            "Radiance states require a dynamic_group_identifier on the target object."
        )
    _apply_radiance_state_update(
        radiance,
        operation=operation,
        states=states,
        state_loader=state_loader,
    )


def edit_honeybee_model(
    *,
    garden_root: str,
    target: dict[str, Any],
    display_name: str | None = None,
    user_data: dict[str, Any] | None = None,
    units: str | None = None,
    convert_geometry: bool = True,
    tolerance: float | None = None,
    angle_tolerance: float | None = None,
    electric_load_center: dict[str, Any] | None = None,
    add_objects: list[dict[str, Any]] | None = None,
    remove_targets: list[dict[str, Any]] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Edit one Honeybee Model by model target."""
    target = normalize_honeybee_model_target(target)
    if target.get("target_type") != "honeybee_model" or target.get("domain") != "honeybee":
        raise ValueError("edit_honeybee_model requires a Honeybee model target.")

    updated_fields: list[str] = []
    if display_name is not None:
        updated_fields.append("display_name")
    if user_data is not None:
        updated_fields.append("user_data")
    if units is not None:
        updated_fields.append("units")
    if tolerance is not None:
        updated_fields.append("tolerance")
    if angle_tolerance is not None:
        updated_fields.append("angle_tolerance")
    if electric_load_center is not None:
        updated_fields.append("electric_load_center")
    if add_objects:
        updated_fields.append("add_objects")
    if remove_targets:
        updated_fields.append("remove_objects")
    _require_edit(updated_fields, "model")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, target)
    model = load_honeybee_model(garden_root, model_target)

    if display_name is not None:
        model.display_name = display_name
    if user_data is not None:
        model.user_data = user_data
    if units is not None:
        if convert_geometry:
            try:
                model.convert_to_units(units)
            except Exception as exc:
                raise ValueError(f"Invalid Honeybee units conversion to {units!r}. {exc}") from exc
        else:
            model.units = units
    if tolerance is not None:
        model.tolerance = tolerance
    if angle_tolerance is not None:
        model.angle_tolerance = angle_tolerance
    if electric_load_center is not None:
        electric_load_center = _library_object_dict_from_target(
            garden_root=garden_root,
            data=electric_load_center,
            field_name="electric_load_center",
            domain="honeybee_energy",
            object_family="electric_load_center",
        )
        model.properties.energy.electric_load_center = _electric_load_center_from_dict(
            electric_load_center
        )
    add_summary = add_objects_to_model(model, add_objects)
    remove_summary = remove_objects_from_model(model, remove_targets)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="edit_honeybee_model",
        target=model_target,
        object_type="model",
        updated_fields=updated_fields,
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_changed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _model_edit_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        object_dict=model.to_dict(),
        updated_fields=updated_fields,
        add_summary=add_summary,
        remove_summary=remove_summary,
        postprocess=postprocess,
    )


def edit_honeybee_face(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    user_data: dict[str, Any] | None = None,
    geometry: dict[str, Any] | None = None,
    type: str | dict[str, Any] | None = None,
    boundary_condition: str | dict[str, Any] | None = None,
    construction: dict[str, Any] | str | None = None,
    vent_crack: dict[str, Any] | None = None,
    modifier: dict[str, Any] | str | None = None,
    modifier_blk: dict[str, Any] | str | None = None,
    reset_fields: list[str] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Edit one Honeybee Face by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "face":
        raise ValueError("edit_honeybee_face requires a face target.")

    updated_fields: list[str] = []
    if display_name is not None:
        updated_fields.append("display_name")
    if user_data is not None:
        updated_fields.append("user_data")
    if geometry is not None:
        updated_fields.append("geometry")
    if type is not None:
        updated_fields.append("type")
    if boundary_condition is not None:
        updated_fields.append("boundary_condition")
    if construction is not None:
        updated_fields.append("construction")
    if vent_crack is not None:
        updated_fields.append("vent_crack")
    if modifier is not None:
        updated_fields.append("modifier")
    if modifier_blk is not None:
        updated_fields.append("modifier_blk")
    validated_resets: list[str] = []
    if reset_fields is not None:
        validated_resets = _validate_reset_fields(reset_fields, object_type="face")
        updated_fields.append("reset_fields")
    _require_edit(updated_fields, "face")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    if construction is not None:
        construction = _library_object_dict_from_target(
            garden_root=garden_root,
            data=construction,
            field_name="construction",
            domain="honeybee_energy",
            object_family="construction",
        )
    if modifier is not None:
        modifier = _library_object_dict_from_target(
            garden_root=garden_root,
            data=modifier,
            field_name="modifier",
            domain="honeybee_radiance",
            object_family="modifier",
        )
    if modifier_blk is not None:
        modifier_blk = _library_object_dict_from_target(
            garden_root=garden_root,
            data=modifier_blk,
            field_name="modifier_blk",
            domain="honeybee_radiance",
            object_family="modifier",
        )

    face = find_object(model, target)
    if not isinstance(face, Face):
        raise ValueError("Target does not resolve to a Honeybee Face.")

    if geometry is not None:
        if target.get("parent", {}).get("room_identifier"):
            raise ValueError(
                "Room-hosted Honeybee Face geometry updates are not supported in this edit slice."
            )
        if face.sub_faces or face.indoor_shades or face.outdoor_shades:
            raise ValueError(
                "Honeybee Face geometry updates are only supported when the Face has no child sub-faces or shades."
            )

        face_dict = face.to_dict()
        face3d_from_dict(geometry)
        face_dict["geometry"] = geometry
        if display_name is not None:
            face_dict["display_name"] = display_name
        if user_data is not None:
            face_dict["user_data"] = user_data
        if type is not None:
            face_dict["face_type"] = _face_type_from_input(type).name
        if boundary_condition is not None:
            face_dict["boundary_condition"] = _boundary_condition_from_input(
                boundary_condition
            ).to_dict()

        edited_face = Face.from_dict(face_dict)
        validate_honeybee_face(edited_face)
        model.remove_faces(face_ids=[face.identifier])
        model.add_face(edited_face)
    else:
        if display_name is not None:
            face.display_name = display_name
        if user_data is not None:
            face.user_data = user_data
        if type is not None:
            face.type = _face_type_from_input(type)
        if boundary_condition is not None:
            face.boundary_condition = _boundary_condition_from_input(boundary_condition)
        validate_honeybee_face(face)
        edited_face = face

    if validated_resets:
        _apply_object_reset_fields(edited_face, validated_resets)
    if construction is not None:
        construction = _validate_face_construction(
            edited_face,
            _construction_from_dict(construction),
        )
        edited_face.properties.energy.construction = construction
    if vent_crack is not None:
        edited_face.properties.energy.vent_crack = _vent_crack_from_dict(vent_crack)
    if modifier is not None:
        edited_face.properties.radiance.modifier = _modifier_from_input(modifier)
    if modifier_blk is not None:
        edited_face.properties.radiance.modifier_blk = _modifier_from_input(modifier_blk)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="edit_honeybee_face",
        target=target,
        object_type="face",
        updated_fields=updated_fields,
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_changed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _edit_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="edit_honeybee_face",
        target=target,
        object_dict=edited_face.to_dict(),
        updated_fields=updated_fields,
        postprocess=postprocess,
    )


def edit_honeybee_room(
    *,
    garden_root: str,
    target: dict[str, Any] | str,
    model_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    user_data: dict[str, Any] | None = None,
    multiplier: int | None = None,
    zone: str | None = None,
    story: str | None = None,
    exclude_floor_area: bool | None = None,
    program_type: dict[str, Any] | str | None = None,
    construction_set: dict[str, Any] | str | None = None,
    hvac: dict[str, Any] | None = None,
    people: dict[str, Any] | None = None,
    lighting: dict[str, Any] | None = None,
    electric_equipment: dict[str, Any] | None = None,
    gas_equipment: dict[str, Any] | None = None,
    service_hot_water: dict[str, Any] | None = None,
    infiltration: dict[str, Any] | None = None,
    ventilation: dict[str, Any] | None = None,
    exhaust: dict[str, Any] | None = None,
    zone_ventilation_fans: Any = None,
    process_loads: Any = None,
    internal_masses: Any = None,
    shw: dict[str, Any] | None = None,
    window_vent_control: dict[str, Any] | None = None,
    daylighting_control: dict[str, Any] | None = None,
    make_plenum: bool | dict[str, Any] | None = None,
    make_ground: dict[str, Any] | str | None = None,
    reset_fields: list[str] | None = None,
    setpoint: dict[str, Any] | None = None,
    modifier_set: dict[str, Any] | str | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Edit one Honeybee Room by typed target."""
    target_input = target

    field_candidates = {
        "display_name": display_name,
        "user_data": user_data,
        "multiplier": multiplier,
        "zone": zone,
        "story": story,
        "exclude_floor_area": exclude_floor_area,
        "program_type": program_type,
        "construction_set": construction_set,
        "hvac": hvac,
        "people": people,
        "lighting": lighting,
        "electric_equipment": electric_equipment,
        "gas_equipment": gas_equipment,
        "service_hot_water": service_hot_water,
        "infiltration": infiltration,
        "ventilation": ventilation,
        "exhaust": exhaust,
        "zone_ventilation_fans": zone_ventilation_fans,
        "process_loads": process_loads,
        "internal_masses": internal_masses,
        "shw": shw,
        "window_vent_control": window_vent_control,
        "daylighting_control": daylighting_control,
        "make_plenum": make_plenum,
        "make_ground": make_ground,
        "reset_fields": reset_fields,
        "setpoint": setpoint,
        "modifier_set": modifier_set,
    }
    updated_fields = [k for k, v in field_candidates.items() if v is not None]
    _require_edit(updated_fields, "room")

    validated_resets: list[str] = []
    if reset_fields is not None:
        validated_resets = _validate_reset_fields(reset_fields, object_type="room")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    if isinstance(target_input, str):
        room_identifier = target_input
        if not any(room.identifier == room_identifier for room in model.rooms):
            raise ValueError(f"Honeybee Room not found: {room_identifier}")
        target = make_honeybee_object_target(
            garden_id=manifest.garden_id,
            model_identifier=str(model_target["model_identifier"]),
            object_type="room",
            object_identifier=room_identifier,
        )
    else:
        target = normalize_honeybee_object_target(target_input)
        if target.get("object_type") != "room":
            raise ValueError("edit_honeybee_room requires a room target.")

    room = find_object(model, target)
    if not isinstance(room, Room):
        raise ValueError("Target does not resolve to a Honeybee Room.")

    if validated_resets:
        _apply_room_reset_fields(room, validated_resets)

    if display_name is not None:
        room.display_name = display_name
    if user_data is not None:
        room.user_data = user_data
    if multiplier is not None:
        if multiplier < 1:
            raise ValueError("multiplier must be greater than or equal to 1.")
        room.multiplier = multiplier
    if zone is not None:
        room.zone = zone
    if story is not None:
        room.story = story
    if exclude_floor_area is not None:
        room.exclude_floor_area = exclude_floor_area
    if program_type is not None:
        program_type = _library_object_dict_from_target(
            garden_root=garden_root,
            data=program_type,
            field_name="program_type",
            domain="honeybee_energy",
            object_family="program_type",
        )
        room.properties.energy.program_type = _program_type_from_input(program_type)
    if construction_set is not None:
        construction_set = _library_object_dict_from_target(
            garden_root=garden_root,
            data=construction_set,
            field_name="construction_set",
            domain="honeybee_energy",
            object_family="construction_set",
        )
        room.properties.energy.construction_set = _construction_set_from_input(
            construction_set
        )
    if hvac is not None:
        hvac = _library_object_dict_from_target(
            garden_root=garden_root,
            data=hvac,
            field_name="hvac",
            domain="honeybee_energy",
            object_family="hvac",
        )
        room.properties.energy.hvac = _hvac_from_dict(hvac)
    for load_field, load_cls in (
        ("people", People),
        ("lighting", Lighting),
        ("electric_equipment", ElectricEquipment),
        ("gas_equipment", GasEquipment),
        ("service_hot_water", ServiceHotWater),
        ("infiltration", Infiltration),
    ):
        load_val = field_candidates[load_field]
        if load_val is not None:
            setattr(
                room.properties.energy,
                load_field,
                _room_load_from_input(
                    load_val,
                    load_cls,
                    field_name=load_field,
                    garden_root=garden_root,
                ),
            )
    if ventilation is not None:
        ventilation = _library_object_dict_from_target(
            garden_root=garden_root,
            data=ventilation,
            field_name="ventilation",
            domain="honeybee_energy",
            object_family="load",
        )
        room.properties.energy.ventilation = _ventilation_from_dict(ventilation)
    if exhaust is not None:
        room.properties.energy.exhaust = _exhaust_from_input(
            exhaust,
            garden_root=garden_root,
        )
    if zone_ventilation_fans is not None:
        operation, fan_inputs = _parse_zone_ventilation_fan_update(
            zone_ventilation_fans
        )
        fans = []
        if operation != "clear":
            for fan_input in fan_inputs:
                fan_input = _library_object_dict_from_target(
                    garden_root=garden_root,
                    data=fan_input,
                    field_name="zone_ventilation_fans",
                    domain="honeybee_energy",
                    object_family="zone_ventilation_fan",
                )
                fans.append(_zone_ventilation_fan_from_dict(fan_input))
        _apply_room_fans_batch(room.properties.energy, operation, fans)
    if process_loads is not None:
        operation, proc_inputs = _parse_process_loads_update(process_loads)
        procs = (
            [_process_from_input(p, garden_root=garden_root) for p in proc_inputs]
            if operation != "clear"
            else []
        )
        _apply_room_process_loads_batch(room.properties.energy, operation, procs)
    if internal_masses is not None:
        operation, mass_inputs = _parse_internal_masses_update(internal_masses)
        masses = (
            [_internal_mass_from_input(m, garden_root=garden_root) for m in mass_inputs]
            if operation != "clear"
            else []
        )
        _apply_room_internal_masses_batch(room.properties.energy, operation, masses)
    if shw is not None:
        room.properties.energy.shw = _shw_from_input(shw, garden_root=garden_root)
    if window_vent_control is not None:
        room.properties.energy.window_vent_control = _window_vent_control_from_input(
            window_vent_control,
            garden_root=garden_root,
        )
    if daylighting_control is not None:
        room.properties.energy.daylighting_control = _daylighting_control_from_input(
            daylighting_control
        )
    if setpoint is not None:
        setpoint = _library_object_dict_from_target(
            garden_root=garden_root,
            data=setpoint,
            field_name="setpoint",
            domain="honeybee_energy",
            object_family="load",
        )
        room.properties.energy.setpoint = _setpoint_from_dict(setpoint)
    if modifier_set is not None:
        modifier_set = _library_object_dict_from_target(
            garden_root=garden_root,
            data=modifier_set,
            field_name="modifier_set",
            domain="honeybee_radiance",
            object_family="modifier_set",
        )
        room.properties.radiance.modifier_set = _modifier_set_from_dict(modifier_set)
    if make_plenum is not None:
        _apply_make_plenum(room, make_plenum)
    if make_ground is not None:
        _apply_make_ground(room, make_ground, garden_root=garden_root)

    validate_honeybee_room(room)
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="edit_honeybee_room",
        target=target,
        object_type="room",
        updated_fields=updated_fields,
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_changed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _edit_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="edit_honeybee_room",
        target=target,
        object_dict=room.to_dict(),
        updated_fields=updated_fields,
        postprocess=postprocess,
    )


def edit_honeybee_shade(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    user_data: dict[str, Any] | None = None,
    geometry: dict[str, Any] | None = None,
    is_detached: bool | None = None,
    construction: dict[str, Any] | None = None,
    transmittance_schedule: dict[str, Any] | None = None,
    pv_properties: dict[str, Any] | None = None,
    modifier: dict[str, Any] | str | None = None,
    modifier_blk: dict[str, Any] | str | None = None,
    dynamic_group_identifier: str | None = None,
    states: Any = None,
    reset_fields: list[str] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Edit one Honeybee Shade by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "shade":
        raise ValueError("edit_honeybee_shade requires a shade target.")

    updated_fields: list[str] = []
    if display_name is not None:
        updated_fields.append("display_name")
    if user_data is not None:
        updated_fields.append("user_data")
    if geometry is not None:
        updated_fields.append("geometry")
    if is_detached is not None:
        updated_fields.append("is_detached")
    if construction is not None:
        updated_fields.append("construction")
    if transmittance_schedule is not None:
        updated_fields.append("transmittance_schedule")
    if pv_properties is not None:
        updated_fields.append("pv_properties")
    if modifier is not None:
        updated_fields.append("modifier")
    if modifier_blk is not None:
        updated_fields.append("modifier_blk")
    if dynamic_group_identifier is not None:
        updated_fields.append("dynamic_group_identifier")
    if states is not None:
        updated_fields.append("states")
    validated_resets: list[str] = []
    if reset_fields is not None:
        validated_resets = _validate_reset_fields(reset_fields, object_type="shade")
        updated_fields.append("reset_fields")
    _require_edit(updated_fields, "shade")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    if construction is not None:
        construction = _library_object_dict_from_target(
            garden_root=garden_root,
            data=construction,
            field_name="construction",
            domain="honeybee_energy",
            object_family="construction",
        )
    if transmittance_schedule is not None:
        transmittance_schedule = _library_object_dict_from_target(
            garden_root=garden_root,
            data=transmittance_schedule,
            field_name="transmittance_schedule",
            domain="honeybee_energy",
            object_family="schedule",
        )
    if pv_properties is not None:
        pv_properties = _library_object_dict_from_target(
            garden_root=garden_root,
            data=pv_properties,
            field_name="pv_properties",
            domain="honeybee_energy",
            object_family="pv_properties",
        )
    if modifier is not None:
        modifier = _library_object_dict_from_target(
            garden_root=garden_root,
            data=modifier,
            field_name="modifier",
            domain="honeybee_radiance",
            object_family="modifier",
        )
    if modifier_blk is not None:
        modifier_blk = _library_object_dict_from_target(
            garden_root=garden_root,
            data=modifier_blk,
            field_name="modifier_blk",
            domain="honeybee_radiance",
            object_family="modifier",
        )

    shade = find_object(model, target)
    if not isinstance(shade, Shade):
        raise ValueError("Target does not resolve to a Honeybee Shade.")
    if is_detached and shade.parent is not None:
        raise ValueError("Hosted Honeybee Shades cannot be set to detached directly.")

    if geometry is None:
        if display_name is not None:
            shade.display_name = display_name
        if user_data is not None:
            shade.user_data = user_data
        if is_detached is not None:
            shade.is_detached = is_detached
        validate_honeybee_shade(shade)
        edited_shade = shade
    else:
        edited_shade = _edited_shade_from_geometry(
            shade,
            geometry=geometry,
            display_name=display_name,
            user_data=user_data,
            is_detached=is_detached,
        )
        if shade.parent is None:
            model.remove_shades(shade_ids=[shade.identifier])
            model.add_shade(edited_shade)
        else:
            _replace_hosted_shade(shade.parent, shade, edited_shade)

    if validated_resets:
        _apply_object_reset_fields(edited_shade, validated_resets)
    _apply_energy_hot_swaps_to_shade(
        edited_shade,
        construction=construction,
        transmittance_schedule=transmittance_schedule,
        pv_properties=pv_properties,
    )
    _apply_radiance_hot_swaps(
        edited_shade,
        modifier=modifier,
        modifier_blk=modifier_blk,
        dynamic_group_identifier=dynamic_group_identifier,
        states=states,
        state_loader=_shade_state_from_dict,
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="edit_honeybee_shade",
        target=target,
        object_type="shade",
        updated_fields=updated_fields,
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_changed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _edit_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="edit_honeybee_shade",
        target=target,
        object_dict=edited_shade.to_dict(),
        updated_fields=updated_fields,
        postprocess=postprocess,
    )


def edit_honeybee_aperture(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    user_data: dict[str, Any] | None = None,
    geometry: dict[str, Any] | None = None,
    is_operable: bool | None = None,
    construction: dict[str, Any] | None = None,
    vent_opening: dict[str, Any] | None = None,
    modifier: dict[str, Any] | str | None = None,
    modifier_blk: dict[str, Any] | str | None = None,
    dynamic_group_identifier: str | None = None,
    states: Any = None,
    reset_fields: list[str] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Edit one Honeybee Aperture by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "aperture":
        raise ValueError("edit_honeybee_aperture requires an aperture target.")

    updated_fields: list[str] = []
    if display_name is not None:
        updated_fields.append("display_name")
    if user_data is not None:
        updated_fields.append("user_data")
    if geometry is not None:
        updated_fields.append("geometry")
    if is_operable is not None:
        updated_fields.append("is_operable")
    if construction is not None:
        updated_fields.append("construction")
    if vent_opening is not None:
        updated_fields.append("vent_opening")
    if modifier is not None:
        updated_fields.append("modifier")
    if modifier_blk is not None:
        updated_fields.append("modifier_blk")
    if dynamic_group_identifier is not None:
        updated_fields.append("dynamic_group_identifier")
    if states is not None:
        updated_fields.append("states")
    validated_resets: list[str] = []
    if reset_fields is not None:
        validated_resets = _validate_reset_fields(reset_fields, object_type="aperture")
        updated_fields.append("reset_fields")
    _require_edit(updated_fields, "aperture")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    if construction is not None:
        construction = _library_object_dict_from_target(
            garden_root=garden_root,
            data=construction,
            field_name="construction",
            domain="honeybee_energy",
            object_family="construction",
        )
    if modifier is not None:
        modifier = _library_object_dict_from_target(
            garden_root=garden_root,
            data=modifier,
            field_name="modifier",
            domain="honeybee_radiance",
            object_family="modifier",
        )
    if modifier_blk is not None:
        modifier_blk = _library_object_dict_from_target(
            garden_root=garden_root,
            data=modifier_blk,
            field_name="modifier_blk",
            domain="honeybee_radiance",
            object_family="modifier",
        )

    aperture = find_object(model, target)
    if not isinstance(aperture, Aperture):
        raise ValueError("Target does not resolve to a Honeybee Aperture.")

    _ensure_supported_surface_edit(
        obj=aperture,
        geometry_changed=geometry is not None,
        state_changed=(
            is_operable is not None and is_operable != aperture.is_operable
        ),
        state_label="is_operable",
    )

    if geometry is None:
        if display_name is not None:
            aperture.display_name = display_name
        if user_data is not None:
            aperture.user_data = user_data
        if is_operable is not None:
            aperture.is_operable = is_operable
        validate_honeybee_aperture(aperture)
        edited_aperture = aperture
    else:
        edited_aperture = _edited_subface_from_geometry(
            aperture,
            geometry=geometry,
            display_name=display_name,
            user_data=user_data,
            state_field="is_operable",
            state_value=is_operable,
        )
        if aperture.parent is None:
            model.remove_apertures(aperture_ids=[aperture.identifier])
            model.add_aperture(edited_aperture)
        else:
            host = aperture.parent
            if not isinstance(host, Face):
                raise ValueError("Hosted aperture parent must be a Honeybee Face.")
            _replace_hosted_subface(
                host,
                aperture,
                edited_aperture,
                list_name="_apertures",
                add_method_name="add_aperture",
            )
            validate_face_sub_faces(host)

    if validated_resets:
        _apply_object_reset_fields(edited_aperture, validated_resets)
    _apply_energy_hot_swaps_to_subface(
        edited_aperture,
        construction=construction,
        vent_opening=vent_opening,
    )
    _apply_radiance_hot_swaps(
        edited_aperture,
        modifier=modifier,
        modifier_blk=modifier_blk,
        dynamic_group_identifier=dynamic_group_identifier,
        states=states,
        state_loader=_subface_state_from_dict,
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="edit_honeybee_aperture",
        target=target,
        object_type="aperture",
        updated_fields=updated_fields,
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_changed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _edit_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="edit_honeybee_aperture",
        target=target,
        object_dict=edited_aperture.to_dict(),
        updated_fields=updated_fields,
        postprocess=postprocess,
    )


def edit_honeybee_door(
    *,
    garden_root: str,
    target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    user_data: dict[str, Any] | None = None,
    geometry: dict[str, Any] | None = None,
    is_glass: bool | None = None,
    construction: dict[str, Any] | None = None,
    vent_opening: dict[str, Any] | None = None,
    modifier: dict[str, Any] | str | None = None,
    modifier_blk: dict[str, Any] | str | None = None,
    dynamic_group_identifier: str | None = None,
    states: Any = None,
    reset_fields: list[str] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Edit one Honeybee Door by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "door":
        raise ValueError("edit_honeybee_door requires a door target.")

    updated_fields: list[str] = []
    if display_name is not None:
        updated_fields.append("display_name")
    if user_data is not None:
        updated_fields.append("user_data")
    if geometry is not None:
        updated_fields.append("geometry")
    if is_glass is not None:
        updated_fields.append("is_glass")
    if construction is not None:
        updated_fields.append("construction")
    if vent_opening is not None:
        updated_fields.append("vent_opening")
    if modifier is not None:
        updated_fields.append("modifier")
    if modifier_blk is not None:
        updated_fields.append("modifier_blk")
    if dynamic_group_identifier is not None:
        updated_fields.append("dynamic_group_identifier")
    if states is not None:
        updated_fields.append("states")
    validated_resets: list[str] = []
    if reset_fields is not None:
        validated_resets = _validate_reset_fields(reset_fields, object_type="door")
        updated_fields.append("reset_fields")
    _require_edit(updated_fields, "door")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    if construction is not None:
        construction = _library_object_dict_from_target(
            garden_root=garden_root,
            data=construction,
            field_name="construction",
            domain="honeybee_energy",
            object_family="construction",
        )
    if modifier is not None:
        modifier = _library_object_dict_from_target(
            garden_root=garden_root,
            data=modifier,
            field_name="modifier",
            domain="honeybee_radiance",
            object_family="modifier",
        )
    if modifier_blk is not None:
        modifier_blk = _library_object_dict_from_target(
            garden_root=garden_root,
            data=modifier_blk,
            field_name="modifier_blk",
            domain="honeybee_radiance",
            object_family="modifier",
        )

    door = find_object(model, target)
    if not isinstance(door, Door):
        raise ValueError("Target does not resolve to a Honeybee Door.")

    _ensure_supported_surface_edit(
        obj=door,
        geometry_changed=geometry is not None,
        state_changed=is_glass is not None and is_glass != door.is_glass,
        state_label="is_glass",
        allow_geometry_update=True,
    )

    if geometry is None:
        if display_name is not None:
            door.display_name = display_name
        if user_data is not None:
            door.user_data = user_data
        if is_glass is not None:
            door.is_glass = is_glass
        validate_honeybee_door(door)
        edited_door = door
    elif isinstance(door.boundary_condition, Surface):
        edited_door = _edit_surface_door_pair_geometry(
            model,
            door,
            geometry=geometry,
            display_name=display_name,
            user_data=user_data,
            is_glass=is_glass,
        )
    else:
        edited_door = _edited_subface_from_geometry(
            door,
            geometry=geometry,
            display_name=display_name,
            user_data=user_data,
            state_field="is_glass",
            state_value=is_glass,
        )
        if door.parent is None:
            model.remove_doors(door_ids=[door.identifier])
            model.add_door(edited_door)
        else:
            host = door.parent
            if not isinstance(host, Face):
                raise ValueError("Hosted door parent must be a Honeybee Face.")
            _replace_hosted_subface(
                host,
                door,
                edited_door,
                list_name="_doors",
                add_method_name="add_door",
            )
            validate_face_sub_faces(host)

    if validated_resets:
        _apply_object_reset_fields(edited_door, validated_resets)
    _apply_energy_hot_swaps_to_subface(
        edited_door,
        construction=construction,
        vent_opening=vent_opening,
    )
    _apply_radiance_hot_swaps(
        edited_door,
        modifier=modifier,
        modifier_blk=modifier_blk,
        dynamic_group_identifier=dynamic_group_identifier,
        states=states,
        state_loader=_subface_state_from_dict,
    )
    model, postprocess = apply_honeybee_postprocess(
        model=model,
        garden_id=manifest.garden_id,
        model_identifier=str(model_target["model_identifier"]),
        operation="edit_honeybee_door",
        target=target,
        object_type="door",
        updated_fields=updated_fields,
        strategy=postprocess_strategy,
    )

    updated_model_target, persisted_path = _save_changed_model(
        garden_root=garden_root,
        manifest=manifest,
        model_target=model_target,
        model=model,
    )
    return _edit_response(
        manifest=manifest,
        updated_model_target=updated_model_target,
        persisted_path=persisted_path,
        operation="edit_honeybee_door",
        target=target,
        object_dict=edited_door.to_dict(),
        updated_fields=updated_fields,
        postprocess=postprocess,
    )



_ROOM_EDIT_FIELDS = {
    "display_name",
    "user_data",
    "multiplier",
    "zone",
    "story",
    "exclude_floor_area",
    "program_type",
    "construction_set",
    "hvac",
    "people",
    "lighting",
    "electric_equipment",
    "gas_equipment",
    "service_hot_water",
    "infiltration",
    "ventilation",
    "exhaust",
    "zone_ventilation_fans",
    "process_loads",
    "internal_masses",
    "shw",
    "window_vent_control",
    "daylighting_control",
    "make_plenum",
    "make_ground",
    "reset_fields",
    "setpoint",
    "modifier_set",
}
_FACE_EDIT_FIELDS = {
    "display_name",
    "user_data",
    "geometry",
    "face_type",
    "boundary_condition",
    "construction",
    "vent_crack",
    "modifier",
    "modifier_blk",
    "reset_fields",
}
_APERTURE_EDIT_FIELDS = {
    "display_name",
    "user_data",
    "geometry",
    "is_operable",
    "construction",
    "vent_opening",
    "modifier",
    "modifier_blk",
    "dynamic_group_identifier",
    "states",
    "reset_fields",
}
_DOOR_EDIT_FIELDS = {
    "display_name",
    "user_data",
    "geometry",
    "is_glass",
    "construction",
    "vent_opening",
    "modifier",
    "modifier_blk",
    "dynamic_group_identifier",
    "states",
    "reset_fields",
}
_SHADE_EDIT_FIELDS = {
    "display_name",
    "user_data",
    "geometry",
    "is_detached",
    "construction",
    "transmittance_schedule",
    "pv_properties",
    "modifier",
    "modifier_blk",
    "dynamic_group_identifier",
    "states",
    "reset_fields",
}
_ALLOWED_EDIT_FIELDS_BY_TYPE = {
    "room": _ROOM_EDIT_FIELDS,
    "face": _FACE_EDIT_FIELDS,
    "aperture": _APERTURE_EDIT_FIELDS,
    "door": _DOOR_EDIT_FIELDS,
    "shade": _SHADE_EDIT_FIELDS,
}
_ENERGY_PROPERTIES_KEYS = (
    "program_type",
    "construction_set",
    "hvac",
    "people",
    "lighting",
    "electric_equipment",
    "gas_equipment",
    "service_hot_water",
    "infiltration",
    "ventilation",
    "exhaust",
    "setpoint",
    "zone_ventilation_fans",
    "process_loads",
    "internal_masses",
    "shw",
    "window_vent_control",
    "daylighting_control",
    "make_plenum",
    "make_ground",
    "reset_fields",
)
_MAX_BATCH_IDENTIFIER_SAMPLE = 5


def _duplicate_hb_obj(value: Any) -> Any:
    duplicate = getattr(value, "duplicate", None)
    return duplicate() if callable(duplicate) else value


def _serialized_hb_obj(value: Any) -> Any:
    to_dict = getattr(value, "to_dict", None)
    return to_dict() if callable(to_dict) else value


def _merge_energy_properties(
    energy_properties: dict[str, Any] | None,
    top_level: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Merge optional energy_properties dict into top-level edit fields."""
    merged = dict(top_level)
    if energy_properties is None:
        return merged, False
    if not isinstance(energy_properties, dict) or not energy_properties:
        raise ValueError(
            "energy_properties must be a non-empty dictionary of Room Energy fields."
        )
    unknown = sorted(set(energy_properties) - set(_ENERGY_PROPERTIES_KEYS))
    if unknown:
        raise ValueError(
            "energy_properties contains unsupported field(s): "
            f"{', '.join(unknown)}. Supported fields: {', '.join(_ENERGY_PROPERTIES_KEYS)}."
        )
    for key, value in energy_properties.items():
        if value is None:
            raise ValueError(f"energy_properties.{key} must not be null.")
        if merged.get(key) is not None:
            raise ValueError(
                f"Provide {key} either at top level or inside energy_properties, not both."
            )
        merged[key] = value
    return merged, True


def _validate_fields_for_object_type(
    provided_fields: list[str],
    object_type: str,
) -> None:
    allowed = _ALLOWED_EDIT_FIELDS_BY_TYPE.get(object_type)
    if allowed is None:
        raise ValueError(
            f"Unsupported Honeybee object_type for editing: {object_type!r}. "
            "Supported types: room, face, aperture, door, shade."
        )
    unsupported = sorted(set(provided_fields) - allowed)
    if unsupported:
        raise ValueError(
            f"Field(s) {', '.join(unsupported)} are not supported when editing a "
            f"Honeybee {object_type}."
        )


def edit_honeybee_objects(
    *,
    garden_root: str,
    target: dict[str, Any] | str | None = None,
    targets: list[dict[str, Any]] | None = None,
    room_identifiers: list[str] | None = None,
    model_target: dict[str, Any] | None = None,
    display_name: str | None = None,
    user_data: dict[str, Any] | None = None,
    geometry: dict[str, Any] | None = None,
    multiplier: int | None = None,
    zone: str | None = None,
    story: str | None = None,
    exclude_floor_area: bool | None = None,
    energy_properties: dict[str, Any] | None = None,
    program_type: dict[str, Any] | str | None = None,
    construction_set: dict[str, Any] | str | None = None,
    hvac: dict[str, Any] | None = None,
    people: dict[str, Any] | None = None,
    lighting: dict[str, Any] | None = None,
    electric_equipment: dict[str, Any] | None = None,
    gas_equipment: dict[str, Any] | None = None,
    service_hot_water: dict[str, Any] | None = None,
    infiltration: dict[str, Any] | None = None,
    ventilation: dict[str, Any] | None = None,
    exhaust: dict[str, Any] | None = None,
    zone_ventilation_fans: Any = None,
    process_loads: Any = None,
    internal_masses: Any = None,
    shw: dict[str, Any] | None = None,
    window_vent_control: dict[str, Any] | None = None,
    daylighting_control: dict[str, Any] | None = None,
    make_plenum: bool | dict[str, Any] | None = None,
    make_ground: dict[str, Any] | str | None = None,
    reset_fields: list[str] | None = None,
    setpoint: dict[str, Any] | None = None,
    modifier_set: dict[str, Any] | str | None = None,
    face_type: str | dict[str, Any] | None = None,
    type: str | dict[str, Any] | None = None,
    boundary_condition: str | dict[str, Any] | None = None,
    vent_crack: dict[str, Any] | None = None,
    is_operable: bool | None = None,
    is_glass: bool | None = None,
    is_detached: bool | None = None,
    construction: dict[str, Any] | str | None = None,
    vent_opening: dict[str, Any] | None = None,
    transmittance_schedule: dict[str, Any] | None = None,
    pv_properties: dict[str, Any] | None = None,
    modifier: dict[str, Any] | str | None = None,
    modifier_blk: dict[str, Any] | str | None = None,
    dynamic_group_identifier: str | None = None,
    states: Any = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Edit one or more Honeybee Room, Face, Aperture, Door, or Shade targets."""
    selector_count = sum(
        selector is not None for selector in (target, targets, room_identifiers)
    )
    if selector_count != 1:
        raise ValueError(
            "Provide exactly one of target, targets, or room_identifiers."
        )

    effective_face_type = face_type if face_type is not None else type
    merged_energy, has_energy_dict = _merge_energy_properties(
        energy_properties,
        {
            "program_type": program_type,
            "construction_set": construction_set,
            "hvac": hvac,
            "people": people,
            "lighting": lighting,
            "electric_equipment": electric_equipment,
            "gas_equipment": gas_equipment,
            "service_hot_water": service_hot_water,
            "infiltration": infiltration,
            "ventilation": ventilation,
            "exhaust": exhaust,
            "setpoint": setpoint,
            "zone_ventilation_fans": zone_ventilation_fans,
            "process_loads": process_loads,
            "internal_masses": internal_masses,
            "shw": shw,
            "window_vent_control": window_vent_control,
            "daylighting_control": daylighting_control,
            "make_plenum": make_plenum,
            "make_ground": make_ground,
            "reset_fields": reset_fields,
        },
    )
    program_type = merged_energy["program_type"]
    construction_set = merged_energy["construction_set"]
    hvac = merged_energy["hvac"]
    people = merged_energy["people"]
    lighting = merged_energy["lighting"]
    electric_equipment = merged_energy["electric_equipment"]
    gas_equipment = merged_energy["gas_equipment"]
    service_hot_water = merged_energy["service_hot_water"]
    infiltration = merged_energy["infiltration"]
    ventilation = merged_energy["ventilation"]
    exhaust = merged_energy["exhaust"]
    setpoint = merged_energy["setpoint"]
    zone_ventilation_fans = merged_energy["zone_ventilation_fans"]
    process_loads = merged_energy["process_loads"]
    internal_masses = merged_energy["internal_masses"]
    shw = merged_energy["shw"]
    window_vent_control = merged_energy["window_vent_control"]
    daylighting_control = merged_energy["daylighting_control"]
    make_plenum = merged_energy["make_plenum"]
    make_ground = merged_energy["make_ground"]
    reset_fields = merged_energy["reset_fields"]

    all_field_values: dict[str, Any] = {
        "display_name": display_name,
        "user_data": user_data,
        "geometry": geometry,
        "multiplier": multiplier,
        "zone": zone,
        "story": story,
        "exclude_floor_area": exclude_floor_area,
        "program_type": program_type,
        "construction_set": construction_set,
        "hvac": hvac,
        "people": people,
        "lighting": lighting,
        "electric_equipment": electric_equipment,
        "gas_equipment": gas_equipment,
        "service_hot_water": service_hot_water,
        "infiltration": infiltration,
        "ventilation": ventilation,
        "exhaust": exhaust,
        "zone_ventilation_fans": zone_ventilation_fans,
        "process_loads": process_loads,
        "internal_masses": internal_masses,
        "shw": shw,
        "window_vent_control": window_vent_control,
        "daylighting_control": daylighting_control,
        "make_plenum": make_plenum,
        "make_ground": make_ground,
        "reset_fields": reset_fields,
        "setpoint": setpoint,
        "modifier_set": modifier_set,
        "face_type": effective_face_type,
        "boundary_condition": boundary_condition,
        "vent_crack": vent_crack,
        "is_operable": is_operable,
        "is_glass": is_glass,
        "is_detached": is_detached,
        "construction": construction,
        "vent_opening": vent_opening,
        "transmittance_schedule": transmittance_schedule,
        "pv_properties": pv_properties,
        "modifier": modifier,
        "modifier_blk": modifier_blk,
        "dynamic_group_identifier": dynamic_group_identifier,
        "states": states,
    }
    updated_fields = [
        name for name, value in all_field_values.items() if value is not None
    ]
    if not updated_fields:
        raise ValueError("edit_honeybee_objects requires at least one edit input.")

    # Single-target fast path preserves exact single-object response contract.
    if target is not None:
        if isinstance(target, str):
            _validate_fields_for_object_type(updated_fields, "room")
            return edit_honeybee_room(
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
                postprocess_strategy=postprocess_strategy,
            )
        norm_target = normalize_honeybee_object_target(target)
        obj_type = str(norm_target.get("object_type"))
        _validate_fields_for_object_type(updated_fields, obj_type)
        if obj_type == "room":
            return edit_honeybee_room(
                garden_root=garden_root,
                target=norm_target,
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
                postprocess_strategy=postprocess_strategy,
            )
        if obj_type == "face":
            return edit_honeybee_face(
                garden_root=garden_root,
                target=norm_target,
                model_target=model_target,
                display_name=display_name,
                user_data=user_data,
                geometry=geometry,
                type=effective_face_type,
                boundary_condition=boundary_condition,
                construction=construction,
                vent_crack=vent_crack,
                modifier=modifier,
                modifier_blk=modifier_blk,
                reset_fields=reset_fields,
                postprocess_strategy=postprocess_strategy,
            )
        if obj_type == "aperture":
            return edit_honeybee_aperture(
                garden_root=garden_root,
                target=norm_target,
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
                reset_fields=reset_fields,
                postprocess_strategy=postprocess_strategy,
            )
        if obj_type == "door":
            return edit_honeybee_door(
                garden_root=garden_root,
                target=norm_target,
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
                reset_fields=reset_fields,
                postprocess_strategy=postprocess_strategy,
            )
        return edit_honeybee_shade(
            garden_root=garden_root,
            target=norm_target,
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
            reset_fields=reset_fields,
            postprocess_strategy=postprocess_strategy,
        )

    # Batch path: targets or room_identifiers
    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    expected_model_id = str(resolved_model_target["model_identifier"])
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    rooms_by_identifier = {room.identifier: room for room in model.rooms}

    normalized_targets: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str]] = set()
    if room_identifiers is not None:
        if not isinstance(room_identifiers, list) or not room_identifiers:
            raise ValueError("room_identifiers must be a non-empty list of strings.")
        _validate_fields_for_object_type(updated_fields, "room")
        for index, identifier in enumerate(room_identifiers):
            if not isinstance(identifier, str) or not identifier.strip():
                raise ValueError(f"room_identifiers[{index}] must be a non-empty string.")
            if identifier not in rooms_by_identifier:
                raise ValueError(f"Honeybee Room not found: {identifier}")
            key = ("room", identifier)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            normalized_targets.append(
                make_honeybee_object_target(
                    garden_id=manifest.garden_id,
                    model_identifier=expected_model_id,
                    object_type="room",
                    object_identifier=identifier,
                )
            )
    else:
        if not isinstance(targets, list) or not targets:
            raise ValueError("targets must be a non-empty list of Honeybee object targets.")
        for index, raw_target in enumerate(targets):
            try:
                norm = normalize_honeybee_object_target(raw_target)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"targets[{index}] must be a Honeybee object typed target."
                ) from exc
            obj_type = str(norm.get("object_type"))
            _validate_fields_for_object_type(updated_fields, obj_type)
            if norm.get("garden_id") != manifest.garden_id:
                raise ValueError(f"targets[{index}] belongs to a different Garden.")
            if norm.get("model_identifier") != expected_model_id:
                raise ValueError(
                    f"targets[{index}] belongs to Honeybee model "
                    f"{norm.get('model_identifier')!r}, expected {expected_model_id!r}."
                )
            key = (obj_type, str(norm["object_identifier"]))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            find_object(model, norm)
            normalized_targets.append(norm)

    # Pre-resolve shared library objects & inputs once before mutating working_model.
    resolved_program_type = None
    if program_type is not None:
        resolved_program_type = _program_type_from_input(
            _library_object_dict_from_target(
                garden_root=garden_root_path,
                data=program_type,
                field_name="program_type",
                domain="honeybee_energy",
                object_family="program_type",
            )
        )
    resolved_construction_set = None
    if construction_set is not None:
        resolved_construction_set = _construction_set_from_input(
            _library_object_dict_from_target(
                garden_root=garden_root_path,
                data=construction_set,
                field_name="construction_set",
                domain="honeybee_energy",
                object_family="construction_set",
            )
        )
    resolved_hvac = None
    if hvac is not None:
        resolved_hvac = _hvac_from_dict(
            _library_object_dict_from_target(
                garden_root=garden_root_path,
                data=hvac,
                field_name="hvac",
                domain="honeybee_energy",
                object_family="hvac",
            )
        )
    resolved_ventilation = None
    if ventilation is not None:
        resolved_ventilation = _ventilation_from_dict(
            _library_object_dict_from_target(
                garden_root=garden_root_path,
                data=ventilation,
                field_name="ventilation",
                domain="honeybee_energy",
                object_family="load",
            )
        )
    resolved_fans: tuple[str, list[Any]] | None = None
    if zone_ventilation_fans is not None:
        fan_op, fan_inputs = _parse_zone_ventilation_fan_update(zone_ventilation_fans)
        fan_objs = []
        for fan_input in fan_inputs:
            fan_dict = _library_object_dict_from_target(
                garden_root=garden_root_path,
                data=fan_input,
                field_name="zone_ventilation_fans",
                domain="honeybee_energy",
                object_family="zone_ventilation_fan",
            )
            fan_objs.append(_zone_ventilation_fan_from_dict(fan_dict))
        resolved_fans = (fan_op, fan_objs)
    resolved_people = (
        _room_load_from_input(people, People, field_name="people", garden_root=garden_root_path)
        if people is not None
        else None
    )
    resolved_lighting = (
        _room_load_from_input(lighting, Lighting, field_name="lighting", garden_root=garden_root_path)
        if lighting is not None
        else None
    )
    resolved_electric_equipment = (
        _room_load_from_input(
            electric_equipment,
            ElectricEquipment,
            field_name="electric_equipment",
            garden_root=garden_root_path,
        )
        if electric_equipment is not None
        else None
    )
    resolved_gas_equipment = (
        _room_load_from_input(
            gas_equipment,
            GasEquipment,
            field_name="gas_equipment",
            garden_root=garden_root_path,
        )
        if gas_equipment is not None
        else None
    )
    resolved_service_hot_water = (
        _room_load_from_input(
            service_hot_water,
            ServiceHotWater,
            field_name="service_hot_water",
            garden_root=garden_root_path,
        )
        if service_hot_water is not None
        else None
    )
    resolved_infiltration = (
        _room_load_from_input(
            infiltration,
            Infiltration,
            field_name="infiltration",
            garden_root=garden_root_path,
        )
        if infiltration is not None
        else None
    )
    resolved_exhaust = (
        _exhaust_from_input(exhaust, garden_root=garden_root_path)
        if exhaust is not None
        else None
    )
    resolved_process_loads: tuple[str, list[Process]] | None = None
    if process_loads is not None:
        proc_op, proc_inputs = _parse_process_loads_update(process_loads)
        proc_objs = (
            [_process_from_input(item, garden_root=garden_root_path) for item in proc_inputs]
            if proc_op != "clear"
            else []
        )
        resolved_process_loads = (proc_op, proc_objs)
    resolved_internal_masses: tuple[str, list[InternalMass]] | None = None
    if internal_masses is not None:
        mass_op, mass_inputs = _parse_internal_masses_update(internal_masses)
        mass_objs = (
            [_internal_mass_from_input(item, garden_root=garden_root_path) for item in mass_inputs]
            if mass_op != "clear"
            else []
        )
        resolved_internal_masses = (mass_op, mass_objs)
    resolved_shw = _shw_from_input(shw, garden_root=garden_root_path) if shw is not None else None
    resolved_window_vent_control = (
        _window_vent_control_from_input(window_vent_control, garden_root=garden_root_path)
        if window_vent_control is not None
        else None
    )
    resolved_daylighting_control = (
        _daylighting_control_from_input(daylighting_control)
        if daylighting_control is not None
        else None
    )
    validated_resets_by_type: dict[str, list[str]] = {}
    if reset_fields is not None:
        for t in {str(norm["object_type"]) for norm in normalized_targets}:
            validated_resets_by_type[t] = _validate_reset_fields(reset_fields, object_type=t)
    resolved_setpoint = None
    if setpoint is not None:
        resolved_setpoint = _setpoint_from_dict(
            _library_object_dict_from_target(
                garden_root=garden_root_path,
                data=setpoint,
                field_name="setpoint",
                domain="honeybee_energy",
                object_family="load",
            )
        )
    resolved_modifier_set = None
    if modifier_set is not None:
        resolved_modifier_set = _modifier_set_from_dict(
            _library_object_dict_from_target(
                garden_root=garden_root_path,
                data=modifier_set,
                field_name="modifier_set",
                domain="honeybee_radiance",
                object_family="modifier_set",
            )
        )
    resolved_construction_dict = None
    if construction is not None:
        resolved_construction_dict = _library_object_dict_from_target(
            garden_root=garden_root_path,
            data=construction,
            field_name="construction",
            domain="honeybee_energy",
            object_family="construction",
        )
    resolved_transmittance_dict = None
    if transmittance_schedule is not None:
        resolved_transmittance_dict = _library_object_dict_from_target(
            garden_root=garden_root_path,
            data=transmittance_schedule,
            field_name="transmittance_schedule",
            domain="honeybee_energy",
            object_family="schedule",
        )
    resolved_pv_dict = None
    if pv_properties is not None:
        resolved_pv_dict = _library_object_dict_from_target(
            garden_root=garden_root_path,
            data=pv_properties,
            field_name="pv_properties",
            domain="honeybee_energy",
            object_family="pv_properties",
        )
    resolved_modifier = None
    if modifier is not None:
        resolved_modifier = _library_object_dict_from_target(
            garden_root=garden_root_path,
            data=modifier,
            field_name="modifier",
            domain="honeybee_radiance",
            object_family="modifier",
        )
    resolved_modifier_blk = None
    if modifier_blk is not None:
        resolved_modifier_blk = _library_object_dict_from_target(
            garden_root=garden_root_path,
            data=modifier_blk,
            field_name="modifier_blk",
            domain="honeybee_radiance",
            object_family="modifier",
        )

    if multiplier is not None and multiplier < 1:
        raise ValueError("multiplier must be greater than or equal to 1.")

    working_model = model.duplicate()
    edited_types: list[str] = []
    edited_identifiers: list[str] = []
    changed_identifiers: list[str] = []
    object_summaries: list[dict[str, Any]] = []

    for norm in normalized_targets:
        obj_type = str(norm["object_type"])
        obj_id = str(norm["object_identifier"])
        obj = find_object(working_model, norm)
        if obj_type not in edited_types:
            edited_types.append(obj_type)
        edited_identifiers.append(obj_id)

        if obj_type == "room":
            if not isinstance(obj, Room):
                raise ValueError(f"Target {obj_id} does not resolve to a Honeybee Room.")
            room_changed = False
            if "room" in validated_resets_by_type:
                if _apply_room_reset_fields(obj, validated_resets_by_type["room"]):
                    room_changed = True
            if display_name is not None:
                obj.display_name = display_name
                room_changed = True
            if user_data is not None:
                obj.user_data = dict(user_data)
                room_changed = True
            if multiplier is not None:
                obj.multiplier = multiplier
                room_changed = True
            if zone is not None:
                obj.zone = zone
                room_changed = True
            if story is not None:
                obj.story = story
                room_changed = True
            if exclude_floor_area is not None:
                obj.exclude_floor_area = exclude_floor_area
                room_changed = True
            energy = obj.properties.energy
            for single_field, resolved_val in (
                ("program_type", resolved_program_type),
                ("construction_set", resolved_construction_set),
                ("hvac", resolved_hvac),
                ("people", resolved_people),
                ("lighting", resolved_lighting),
                ("electric_equipment", resolved_electric_equipment),
                ("gas_equipment", resolved_gas_equipment),
                ("service_hot_water", resolved_service_hot_water),
                ("infiltration", resolved_infiltration),
                ("ventilation", resolved_ventilation),
                ("exhaust", resolved_exhaust),
                ("shw", resolved_shw),
                ("window_vent_control", resolved_window_vent_control),
                ("daylighting_control", resolved_daylighting_control),
                ("setpoint", resolved_setpoint),
            ):
                if resolved_val is None:
                    continue
                current_private = getattr(energy, f"_{single_field}", None)
                if _serialized_hb_obj(current_private) != _serialized_hb_obj(resolved_val):
                    setattr(energy, single_field, _duplicate_hb_obj(resolved_val))
                    room_changed = True
            if resolved_fans is not None:
                if _apply_room_fans_batch(energy, resolved_fans[0], resolved_fans[1]):
                    room_changed = True
            if resolved_process_loads is not None:
                if _apply_room_process_loads_batch(
                    energy, resolved_process_loads[0], resolved_process_loads[1]
                ):
                    room_changed = True
            if resolved_internal_masses is not None:
                if _apply_room_internal_masses_batch(
                    energy, resolved_internal_masses[0], resolved_internal_masses[1]
                ):
                    room_changed = True
            if resolved_modifier_set is not None:
                obj.properties.radiance.modifier_set = _duplicate_hb_obj(
                    resolved_modifier_set
                )
                room_changed = True
            if make_plenum is not None:
                _apply_make_plenum(obj, make_plenum)
                room_changed = True
            if make_ground is not None:
                _apply_make_ground(obj, make_ground, garden_root=garden_root_path)
                room_changed = True
            validate_honeybee_room(obj)
            if room_changed:
                changed_identifiers.append(obj_id)
            if len(object_summaries) < 20:
                object_summaries.append(object_summary(norm, obj.to_dict()))

        elif obj_type == "face":
            if not isinstance(obj, Face):
                raise ValueError(f"Target {obj_id} does not resolve to a Honeybee Face.")
            if geometry is not None:
                if norm.get("parent", {}).get("room_identifier"):
                    raise ValueError(
                        "Room-hosted Honeybee Face geometry updates are not supported in this edit slice."
                    )
                if obj.sub_faces or obj.indoor_shades or obj.outdoor_shades:
                    raise ValueError(
                        "Honeybee Face geometry updates are only supported when the Face has no child sub-faces or shades."
                    )
                face_dict = obj.to_dict()
                face3d_from_dict(geometry)
                face_dict["geometry"] = geometry
                if display_name is not None:
                    face_dict["display_name"] = display_name
                if user_data is not None:
                    face_dict["user_data"] = dict(user_data)
                if effective_face_type is not None:
                    face_dict["face_type"] = _face_type_from_input(
                        effective_face_type
                    ).name
                if boundary_condition is not None:
                    face_dict["boundary_condition"] = _boundary_condition_from_input(
                        boundary_condition
                    ).to_dict()
                edited_face = Face.from_dict(face_dict)
                validate_honeybee_face(edited_face)
                working_model.remove_faces(face_ids=[obj.identifier])
                working_model.add_face(edited_face)
            else:
                if display_name is not None:
                    obj.display_name = display_name
                if user_data is not None:
                    obj.user_data = dict(user_data)
                if effective_face_type is not None:
                    obj.type = _face_type_from_input(effective_face_type)
                if boundary_condition is not None:
                    obj.boundary_condition = _boundary_condition_from_input(
                        boundary_condition
                    )
                validate_honeybee_face(obj)
                edited_face = obj
            if "face" in validated_resets_by_type:
                _apply_object_reset_fields(edited_face, validated_resets_by_type["face"])
            if resolved_construction_dict is not None:
                const_obj = _validate_face_construction(
                    edited_face,
                    _construction_from_dict(resolved_construction_dict),
                )
                edited_face.properties.energy.construction = _duplicate_hb_obj(const_obj)
            if vent_crack is not None:
                edited_face.properties.energy.vent_crack = _duplicate_hb_obj(
                    _vent_crack_from_dict(vent_crack)
                )
            if resolved_modifier is not None:
                edited_face.properties.radiance.modifier = _duplicate_hb_obj(
                    _modifier_from_input(resolved_modifier)
                )
            if resolved_modifier_blk is not None:
                edited_face.properties.radiance.modifier_blk = _duplicate_hb_obj(
                    _modifier_from_input(resolved_modifier_blk)
                )
            changed_identifiers.append(obj_id)
            if len(object_summaries) < 20:
                object_summaries.append(object_summary(norm, edited_face.to_dict()))

        elif obj_type == "aperture":
            if not isinstance(obj, Aperture):
                raise ValueError(
                    f"Target {obj_id} does not resolve to a Honeybee Aperture."
                )
            _ensure_supported_surface_edit(
                obj=obj,
                geometry_changed=geometry is not None,
                state_changed=(
                    is_operable is not None and is_operable != obj.is_operable
                ),
                state_label="is_operable",
            )
            if geometry is None:
                if display_name is not None:
                    obj.display_name = display_name
                if user_data is not None:
                    obj.user_data = dict(user_data)
                if is_operable is not None:
                    obj.is_operable = is_operable
                validate_honeybee_aperture(obj)
                edited_ap = obj
            else:
                edited_ap = _edited_subface_from_geometry(
                    obj,
                    geometry=geometry,
                    display_name=display_name,
                    user_data=dict(user_data) if user_data is not None else None,
                    state_field="is_operable",
                    state_value=is_operable,
                )
                if obj.parent is None:
                    working_model.remove_apertures(aperture_ids=[obj.identifier])
                    working_model.add_aperture(edited_ap)
                else:
                    host = obj.parent
                    if not isinstance(host, Face):
                        raise ValueError("Hosted aperture parent must be a Honeybee Face.")
                    _replace_hosted_subface(
                        host,
                        obj,
                        edited_ap,
                        list_name="_apertures",
                        add_method_name="add_aperture",
                    )
                    validate_face_sub_faces(host)
            if "aperture" in validated_resets_by_type:
                _apply_object_reset_fields(edited_ap, validated_resets_by_type["aperture"])
            _apply_energy_hot_swaps_to_subface(
                edited_ap,
                construction=resolved_construction_dict,
                vent_opening=vent_opening,
            )
            _apply_radiance_hot_swaps(
                edited_ap,
                modifier=resolved_modifier,
                modifier_blk=resolved_modifier_blk,
                dynamic_group_identifier=dynamic_group_identifier,
                states=states,
                state_loader=_subface_state_from_dict,
            )
            changed_identifiers.append(obj_id)
            if len(object_summaries) < 20:
                object_summaries.append(object_summary(norm, edited_ap.to_dict()))

        elif obj_type == "door":
            if not isinstance(obj, Door):
                raise ValueError(f"Target {obj_id} does not resolve to a Honeybee Door.")
            _ensure_supported_surface_edit(
                obj=obj,
                geometry_changed=geometry is not None,
                state_changed=is_glass is not None and is_glass != obj.is_glass,
                state_label="is_glass",
                allow_geometry_update=True,
            )
            if geometry is None:
                if display_name is not None:
                    obj.display_name = display_name
                if user_data is not None:
                    obj.user_data = dict(user_data)
                if is_glass is not None:
                    obj.is_glass = is_glass
                validate_honeybee_door(obj)
                edited_door = obj
            elif isinstance(obj.boundary_condition, Surface):
                edited_door = _edit_surface_door_pair_geometry(
                    working_model,
                    obj,
                    geometry=geometry,
                    display_name=display_name,
                    user_data=dict(user_data) if user_data is not None else None,
                    is_glass=is_glass,
                )
            else:
                edited_door = _edited_subface_from_geometry(
                    obj,
                    geometry=geometry,
                    display_name=display_name,
                    user_data=dict(user_data) if user_data is not None else None,
                    state_field="is_glass",
                    state_value=is_glass,
                )
                if obj.parent is None:
                    working_model.remove_doors(door_ids=[obj.identifier])
                    working_model.add_door(edited_door)
                else:
                    host = obj.parent
                    if not isinstance(host, Face):
                        raise ValueError("Hosted door parent must be a Honeybee Face.")
                    _replace_hosted_subface(
                        host,
                        obj,
                        edited_door,
                        list_name="_doors",
                        add_method_name="add_door",
                    )
                    validate_face_sub_faces(host)
            if "door" in validated_resets_by_type:
                _apply_object_reset_fields(edited_door, validated_resets_by_type["door"])
            _apply_energy_hot_swaps_to_subface(
                edited_door,
                construction=resolved_construction_dict,
                vent_opening=vent_opening,
            )
            _apply_radiance_hot_swaps(
                edited_door,
                modifier=resolved_modifier,
                modifier_blk=resolved_modifier_blk,
                dynamic_group_identifier=dynamic_group_identifier,
                states=states,
                state_loader=_subface_state_from_dict,
            )
            changed_identifiers.append(obj_id)
            if len(object_summaries) < 20:
                object_summaries.append(object_summary(norm, edited_door.to_dict()))

        elif obj_type == "shade":
            if not isinstance(obj, Shade):
                raise ValueError(f"Target {obj_id} does not resolve to a Honeybee Shade.")
            if is_detached and obj.parent is not None:
                raise ValueError("Hosted Honeybee Shades cannot be set to detached directly.")
            if geometry is None:
                if display_name is not None:
                    obj.display_name = display_name
                if user_data is not None:
                    obj.user_data = dict(user_data)
                if is_detached is not None:
                    obj.is_detached = is_detached
                validate_honeybee_shade(obj)
                edited_shade = obj
            else:
                edited_shade = _edited_shade_from_geometry(
                    obj,
                    geometry=geometry,
                    display_name=display_name,
                    user_data=dict(user_data) if user_data is not None else None,
                    is_detached=is_detached,
                )
                if obj.parent is None:
                    working_model.remove_shades(shade_ids=[obj.identifier])
                    working_model.add_shade(edited_shade)
                else:
                    _replace_hosted_shade(obj.parent, obj, edited_shade)
            if "shade" in validated_resets_by_type:
                _apply_object_reset_fields(edited_shade, validated_resets_by_type["shade"])
            _apply_energy_hot_swaps_to_shade(
                edited_shade,
                construction=resolved_construction_dict,
                transmittance_schedule=resolved_transmittance_dict,
                pv_properties=resolved_pv_dict,
            )
            _apply_radiance_hot_swaps(
                edited_shade,
                modifier=resolved_modifier,
                modifier_blk=resolved_modifier_blk,
                dynamic_group_identifier=dynamic_group_identifier,
                states=states,
                state_loader=_shade_state_from_dict,
            )
            changed_identifiers.append(obj_id)
            if len(object_summaries) < 20:
                object_summaries.append(object_summary(norm, edited_shade.to_dict()))

    pure_room_energy_only = (
        edited_types == ["room"]
        and (
            has_energy_dict
            or all(field in _ENERGY_PROPERTIES_KEYS for field in updated_fields)
        )
    )
    if (
        pure_room_energy_only
        and not changed_identifiers
        and postprocess_strategy in {None, "none"}
    ):
        sample = edited_identifiers[:_MAX_BATCH_IDENTIFIER_SAMPLE]
        summary_view = {
            "model_target": resolved_model_target,
            "edited_count": 0,
            "requested_count": len(normalized_targets),
            "room_count": len(normalized_targets),
            "updated_room_count": 0,
            "updated_fields": updated_fields,
            "object_types": edited_types,
            "room_identifiers_sample": sample,
            "updated_room_identifiers_sample": [],
        }
        return {
            "target": normalized_targets[0],
            "targets": normalized_targets,
            "model_target": resolved_model_target,
            "runtime_status": "no_change",
            "summary_view": summary_view,
            "persistence_receipt": make_persistence_receipt(
                status="no_change",
                garden_id=manifest.garden_id,
                model_target=resolved_model_target,
                persisted_path=str(resolved_model_target.get("path", "")),
                change_summary={
                    "operation": "edit_honeybee_objects",
                    "targets": normalized_targets,
                    "updated_fields": updated_fields,
                    "edited_count": 0,
                    "updated_room_count": 0,
                },
            ),
            "report": make_report(
                status="ok",
                message="Honeybee Room Energy properties already match the requested values.",
            ),
        }

    postprocess_fields = [
        "type" if field == "face_type" else field for field in updated_fields
    ]
    working_model, postprocess = apply_honeybee_postprocess(
        model=working_model,
        garden_id=manifest.garden_id,
        model_identifier=expected_model_id,
        operation="edit_honeybee_objects",
        target=normalized_targets[0],
        object_type=edited_types[0] if len(edited_types) == 1 else None,
        object_types=edited_types,
        updated_fields=postprocess_fields,
        strategy=postprocess_strategy,
    )
    updated_model_target, persisted_path = _save_changed_model(
        garden_root=garden_root_path,
        manifest=manifest,
        model_target=resolved_model_target,
        model=working_model,
    )
    summary_view: dict[str, Any] = {
        "model_target": updated_model_target,
        "edited_count": len(normalized_targets),
        "requested_count": len(normalized_targets),
        "updated_fields": updated_fields,
        "object_types": edited_types,
        "edited_identifiers": edited_identifiers,
        "objects": object_summaries,
    }
    if edited_types == ["room"]:
        summary_view["room_count"] = len(normalized_targets)
        summary_view["updated_room_count"] = len(changed_identifiers)
        summary_view["room_identifiers_sample"] = edited_identifiers[
            :_MAX_BATCH_IDENTIFIER_SAMPLE
        ]
        summary_view["updated_room_identifiers_sample"] = changed_identifiers[
            :_MAX_BATCH_IDENTIFIER_SAMPLE
        ]

    return attach_postprocess_result(
        {
            "target": normalized_targets[0],
            "targets": normalized_targets,
            "model_target": updated_model_target,
            "summary_view": summary_view,
            "persistence_receipt": make_persistence_receipt(
                status="persisted",
                garden_id=manifest.garden_id,
                base_honeybee_model_changed=(
                    manifest.base_honeybee_model == resolved_model_target
                ),
                model_target=updated_model_target,
                persisted_path=persisted_path,
                change_summary={
                    "operation": "edit_honeybee_objects",
                    "targets": normalized_targets,
                    "updated_fields": updated_fields,
                    "object_types": edited_types,
                    "edited_count": len(normalized_targets),
                },
            ),
            "report": make_report(
                status="ok",
                message=(
                    f"Edited {len(normalized_targets)} Honeybee object(s) "
                    f"({', '.join(edited_types)})."
                ),
            ),
        },
        postprocess,
    )
