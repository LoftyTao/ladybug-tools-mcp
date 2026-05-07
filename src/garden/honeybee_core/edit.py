"""Honeybee object edit services."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.aperture import Aperture
from honeybee.boundarycondition import Surface, boundary_conditions
from honeybee.door import Door
from honeybee.face import Face
from honeybee.facetype import face_types
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.dictutil import dict_to_object
from honeybee_energy.construction.dictutil import dict_to_construction
from honeybee_energy.generator.loadcenter import ElectricLoadCenter
from honeybee_energy.generator.pv import PVProperties
from honeybee_energy.hvac import HVAC_TYPES_DICT
from honeybee_energy.hvac._base import _HVACSystem
from honeybee_energy.lib.constructionsets import construction_set_by_identifier
from honeybee_energy.lib.programtypes import program_type_by_identifier
from honeybee_energy.lib.schedules import schedule_by_identifier
from honeybee_energy.load.setpoint import Setpoint
from honeybee_energy.load.ventilation import Ventilation
from honeybee_energy.programtype import ProgramType
from honeybee_energy.schedule.dictutil import dict_to_schedule
from honeybee_energy.ventcool.crack import AFNCrack
from honeybee_energy.ventcool.fan import VentilationFan
from honeybee_energy.ventcool.opening import VentilationOpening
from honeybee_radiance.dynamic.state import RadianceShadeState, RadianceSubFaceState
from honeybee_radiance.lib.modifiers import modifier_by_identifier
from honeybee_radiance.modifier.modifierbase import Modifier
from honeybee_radiance.modifierset import ModifierSet
from honeybee_radiance.mutil import dict_to_modifier

from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
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
    with_honeybee_model_write_lock,
)
from garden.honeybee_core.postprocess import (
    apply_honeybee_postprocess,
    attach_postprocess_result,
)
from garden.honeybee_core.relate import _project_subface_to_face
from garden.honeybee_core.targets import (
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
        set_base=manifest.base_model == model_target,
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


def _modifier_from_dict(data: dict[str, Any]) -> Modifier:
    return _modifier_from_input(data)


def _construction_from_dict(data: dict[str, Any]) -> Any:
    try:
        return dict_to_construction(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Honeybee Energy construction input. {exc}") from exc


def _schedule_from_dict(data: dict[str, Any]) -> Any:
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
        if not isinstance(type_name, str):
            raise ValueError("boundary_condition dict must include a type field.")
        normalized = type_name.replace("_", "").replace(" ", "").lower()
        if normalized == "surface":
            raise ValueError(
                "Surface boundary condition updates are not supported in this edit slice."
            )
        try:
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
    object_family: str,
) -> dict[str, Any]:
    if isinstance(data, dict) and isinstance(data.get("target"), dict):
        data = data["target"]
    if not isinstance(data, dict) or data.get("target_type") != "garden_properties_library_object":
        return data
    if data.get("domain") != domain or data.get("object_family") != object_family:
        raise ValueError(
            f"{field_name} target must reference {domain}:{object_family}."
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


def _parse_zone_ventilation_fan_update(data: Any) -> tuple[str, list[Any]]:
    if isinstance(data, list):
        return "replace_all", data
    if not isinstance(data, dict):
        return "replace_all", [data]
    if data.get("target_type") == "garden_properties_library_object" or data.get("type") == "VentilationFan":
        return "replace_all", [data]

    operation = str(data.get("operation", "replace_all"))
    if operation not in {"replace_all", "add", "clear"}:
        raise ValueError(
            "zone_ventilation_fans.operation must be replace_all, add, or clear."
        )
    if operation == "clear":
        return operation, []
    fans = data.get("fans", data.get("zone_ventilation_fans", []))
    if not isinstance(fans, list):
        raise ValueError("zone_ventilation_fans.fans must be a list.")
    return operation, fans


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


def _modifier_set_from_dict(data: dict[str, Any]) -> ModifierSet:
    try:
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


@with_honeybee_model_write_lock
def edit_honeybee_model(
    *,
    garden_root: str,
    target: dict[str, Any],
    display_name: str | None = None,
    user_data: dict[str, Any] | None = None,
    units: str | None = None,
    tolerance: float | None = None,
    angle_tolerance: float | None = None,
    electric_load_center: dict[str, Any] | None = None,
    add_objects: list[dict[str, Any]] | None = None,
    remove_targets: list[dict[str, Any]] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Edit one Honeybee Model by model target."""
    target = normalize_honeybee_model_target(target)
    if target.get("target_type") != "model" or target.get("domain") != "honeybee":
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


@with_honeybee_model_write_lock
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
    construction: dict[str, Any] | None = None,
    vent_crack: dict[str, Any] | None = None,
    modifier: dict[str, Any] | str | None = None,
    modifier_blk: dict[str, Any] | str | None = None,
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

    if construction is not None:
        construction = _construction_from_dict(construction)
        if not isinstance(construction, OpaqueConstruction):
            raise ValueError("construction must resolve to a Honeybee opaque construction.")
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


@with_honeybee_model_write_lock
def edit_honeybee_room(
    *,
    garden_root: str,
    target: dict[str, Any],
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
    ventilation: dict[str, Any] | None = None,
    zone_ventilation_fans: Any = None,
    setpoint: dict[str, Any] | None = None,
    modifier_set: dict[str, Any] | None = None,
    postprocess_strategy: str | None = None,
) -> dict[str, Any]:
    """Edit one Honeybee Room by typed target."""
    target = normalize_honeybee_object_target(target)
    if target.get("object_type") != "room":
        raise ValueError("edit_honeybee_room requires a room target.")

    updated_fields: list[str] = []
    if display_name is not None:
        updated_fields.append("display_name")
    if user_data is not None:
        updated_fields.append("user_data")
    if multiplier is not None:
        updated_fields.append("multiplier")
    if zone is not None:
        updated_fields.append("zone")
    if story is not None:
        updated_fields.append("story")
    if exclude_floor_area is not None:
        updated_fields.append("exclude_floor_area")
    if program_type is not None:
        updated_fields.append("program_type")
    if construction_set is not None:
        updated_fields.append("construction_set")
    if hvac is not None:
        updated_fields.append("hvac")
    if ventilation is not None:
        updated_fields.append("ventilation")
    if zone_ventilation_fans is not None:
        updated_fields.append("zone_ventilation_fans")
    if setpoint is not None:
        updated_fields.append("setpoint")
    if modifier_set is not None:
        updated_fields.append("modifier_set")
    _require_edit(updated_fields, "room")

    garden_root = Path(garden_root).expanduser().resolve()
    manifest, model_target = resolve_model_target(garden_root, model_target)
    model = load_honeybee_model(garden_root, model_target)

    room = find_object(model, target)
    if not isinstance(room, Room):
        raise ValueError("Target does not resolve to a Honeybee Room.")

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
    if ventilation is not None:
        ventilation = _library_object_dict_from_target(
            garden_root=garden_root,
            data=ventilation,
            field_name="ventilation",
            domain="honeybee_energy",
            object_family="load",
        )
        room.properties.energy.ventilation = _ventilation_from_dict(ventilation)
    if zone_ventilation_fans is not None:
        operation, fan_inputs = _parse_zone_ventilation_fan_update(
            zone_ventilation_fans
        )
        if operation == "clear":
            room.properties.energy.remove_fans()
        else:
            fans = []
            for fan_input in fan_inputs:
                fan_input = _library_object_dict_from_target(
                    garden_root=garden_root,
                    data=fan_input,
                    field_name="zone_ventilation_fans",
                    domain="honeybee_energy",
                    object_family="zone_ventilation_fan",
                )
                fans.append(_zone_ventilation_fan_from_dict(fan_input))
            if operation == "replace_all":
                room.properties.energy.remove_fans()
            for fan in fans:
                room.properties.energy.add_fan(fan)
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


@with_honeybee_model_write_lock
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


@with_honeybee_model_write_lock
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


@with_honeybee_model_write_lock
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
