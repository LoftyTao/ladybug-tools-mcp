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
from honeybee_energy.construction.dictutil import dict_to_construction
from honeybee_energy.construction.shade import ShadeConstruction
from honeybee_energy.constructionset import ConstructionSet
from honeybee_energy.hvac import HVAC_TYPES_DICT
from honeybee_energy.hvac.idealair import IdealAirSystem
from honeybee_energy.lib.constructions import (
    opaque_construction_by_identifier,
    shade_construction_by_identifier,
)
from honeybee_energy.lib.constructionsets import construction_set_by_identifier
from honeybee_energy.lib.programtypes import program_type_by_identifier
from honeybee_energy.lib.schedules import schedule_by_identifier
from honeybee_energy.load.daylight import DaylightingControl
from honeybee_energy.load.process import Process
from honeybee_energy.programtype import ProgramType
from honeybee_energy.schedule.dictutil import dict_to_schedule
from honeybee_energy.shw import SHWSystem
from honeybee_energy.ventcool.control import VentilationControl
from honeybee_energy.ventcool.fan import VentilationFan
from honeybee_energy.ventcool.opening import VentilationOpening
from honeybee_radiance.dictutil import dict_to_object as dict_to_radiance_object
from honeybee_radiance.lib.modifiers import modifier_by_identifier
from honeybee_radiance.lib.modifiersets import modifier_set_by_identifier
from honeybee_radiance.modifier.modifierbase import Modifier
from honeybee_radiance.modifierset import ModifierSet
from ladybug_geometry.geometry3d import Vector3D

from garden.dragonfly_core.model_io import (
    load_dragonfly_model,
    resolve_model_target,
    save_dragonfly_model,
)
from garden.dragonfly_core.targets import normalize_dragonfly_object_target
from garden.libraries.properties import (
    get_garden_properties_library_object,
    search_garden_properties_library_objects,
)
from ladybug_tools_mcp.contracts import make_persistence_receipt, make_report


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

    context_shades = [_host_summary(shade) for shade in model.context_shades]

    summary_view = {
        "garden_target": manifest.target(),
        "model_target": resolved_model_target,
        "model": _host_summary(model),
        "buildings": buildings,
        "stories": stories,
        "room2ds": room2ds,
        "context_shades": context_shades,
        "counts": {
            "buildings": len(buildings),
            "stories": len(stories),
            "room2ds": len(room2ds),
            "context_shades": len(context_shades),
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


def _resolve_custom_or_standards(
    garden_root: str,
    value: Any,
    *,
    domain: str,
    object_family: str,
    standards_lookup: Any,
    dict_loader: Any,
) -> Any:
    if isinstance(value, dict):
        if value.get("target_type") == "garden_properties_library_object":
            loaded = get_garden_properties_library_object(
                garden_root=garden_root,
                target=value,
            )
            return dict_loader(loaded["object_dict"])
        return dict_loader(value)
    if isinstance(value, str):
        if standards_lookup is not None:
            try:
                return standards_lookup(value)
            except Exception:
                pass
        search_res = search_garden_properties_library_objects(
            garden_root=garden_root,
            query=value,
            domain=domain,
            object_family=object_family,
            limit=50,
        )
        for item in search_res.get("matches", []):
            if item.get("identifier") == value and isinstance(item.get("target"), dict):
                loaded = get_garden_properties_library_object(
                    garden_root=garden_root,
                    target=item["target"],
                )
                return dict_loader(loaded["object_dict"])
        if standards_lookup is not None:
            return standards_lookup(value)
        raise ValueError(
            f"Could not resolve {domain}:{object_family} '{value}' in standards or Garden library."
        )
    raise ValueError(f"Expected identifier, dict, or Garden Properties Library target for {object_family}.")


def _load_hvac_dict(data: dict[str, Any]) -> Any:
    hvac_type = data.get("type")
    cls = HVAC_TYPES_DICT.get(str(hvac_type or ""))
    if cls is None:
        raise ValueError(f"Unsupported Honeybee Energy HVAC type: {hvac_type}")
    return cls.from_dict(data)


def _resolve_hvac(garden_root: str, value: Any) -> Any:
    if isinstance(value, str) and value.strip().lower() in {"idealair", "idealairsystem", "ideal_air"}:
        return IdealAirSystem(identifier="IdealAirSystem")
    return _resolve_custom_or_standards(
        garden_root,
        value,
        domain="honeybee_energy",
        object_family="hvac",
        standards_lookup=None,
        dict_loader=_load_hvac_dict,
    )


def _load_modifier_object(data: dict[str, Any]) -> Modifier:
    obj = dict_to_radiance_object(data)
    if not isinstance(obj, Modifier) or isinstance(obj, ModifierSet):
        raise ValueError("Expected Radiance Modifier dictionary.")
    return obj


def _load_modifier_set_object(data: dict[str, Any]) -> ModifierSet:
    obj = dict_to_radiance_object(data)
    if not isinstance(obj, ModifierSet):
        raise ValueError("Expected Radiance ModifierSet dictionary.")
    return obj


def _coerce_daylighting_control(data: dict[str, Any], room: Any) -> DaylightingControl:
    payload = dict(data)
    payload.setdefault("type", "DaylightingControl")
    if payload.get("sensor_position") is None:
        center = room.floor_geometry.center
        payload["sensor_position"] = [float(center.x), float(center.y), float(room.floor_height) + 0.8]
    return DaylightingControl.from_dict(payload)


def _coerce_ventilation_control(data: dict[str, Any]) -> VentilationControl:
    payload = dict(data)
    payload.setdefault("type", "VentilationControl")
    for alias, canonical in (
        ("min_indoor_temp", "min_indoor_temperature"),
        ("max_indoor_temp", "max_indoor_temperature"),
        ("min_outdoor_temp", "min_outdoor_temperature"),
        ("max_outdoor_temp", "max_outdoor_temperature"),
        ("delta_temp", "delta_temperature"),
    ):
        if alias in payload and canonical not in payload:
            payload[canonical] = payload.pop(alias)
    return VentilationControl.from_dict(payload)


def _coerce_ventilation_opening(data: dict[str, Any]) -> VentilationOpening:
    payload = dict(data)
    payload.setdefault("type", "VentilationOpening")
    return VentilationOpening.from_dict(payload)


def _load_fan_dict(data: dict[str, Any]) -> VentilationFan:
    payload = dict(data)
    payload.setdefault("type", "VentilationFan")
    if "name" in payload and "identifier" not in payload:
        payload["identifier"] = payload.pop("name")
    if "motor_efficiency" in payload and "efficiency" not in payload:
        payload["efficiency"] = payload.pop("motor_efficiency")
    if isinstance(payload.get("control"), dict):
        ctrl_dict = dict(payload["control"])
        ctrl_dict.setdefault("type", "VentilationControl")
        payload["control"] = ctrl_dict
    return VentilationFan.from_dict(payload)


def _load_process_dict(data: dict[str, Any]) -> Process:
    payload = dict(data)
    payload.setdefault("type", "Process")
    if "name" in payload and "identifier" not in payload:
        payload["identifier"] = payload.pop("name")
    return Process.from_dict(payload)


def _load_shw_dict(data: dict[str, Any]) -> SHWSystem:
    payload = dict(data)
    payload.setdefault("type", "SHWSystem")
    return SHWSystem.from_dict(payload)


def _load_shade_construction_dict(data: dict[str, Any]) -> ShadeConstruction:
    payload = dict(data)
    payload.setdefault("type", "ShadeConstruction")
    return ShadeConstruction.from_dict(payload)


def _target_rooms(host: Any, host_type: str) -> list[Any]:
    if host_type == "room2d":
        return [host]
    if host_type == "story":
        return list(host.room_2ds)
    if host_type == "building":
        return list(host.unique_room_2ds)
    if host_type == "model":
        return list(host.room_2ds)
    return []


def apply_dragonfly_energy_properties(
    *,
    garden_root: str,
    host_target: dict[str, Any] | None = None,
    model_target: dict[str, Any] | None = None,
    program_type_identifier: str | None = None,
    construction_set_identifier: str | None = None,
    program_type: Any = None,
    construction_set: Any = None,
    hvac: Any = None,
    shw: Any = None,
    person_count: float | None = None,
    lighting_watts: float | None = None,
    electric_equipment_watts: float | None = None,
    gas_equipment_watts: float | None = None,
    hot_water_flow: float | None = None,
    infiltration_ach: float | None = None,
    daylighting_control: dict[str, Any] | None = None,
    daylight_center: dict[str, Any] | None = None,
    window_vent_control: dict[str, Any] | None = None,
    window_vent_opening: dict[str, Any] | None = None,
    fans: list[Any] | None = None,
    remove_existing_fans: bool = False,
    process_loads: list[Any] | None = None,
    remove_existing_process_loads: bool = False,
    diversify: dict[str, Any] | bool | None = None,
    ceiling_plenum_construction: Any = None,
    floor_plenum_construction: Any = None,
    construction: Any = None,
    transmittance_schedule: Any = None,
) -> dict[str, Any]:
    """Apply Energy properties (standards, Garden library, HVAC, loads, plenums, shade) to a host."""
    resolved_prog_in = program_type if program_type is not None else program_type_identifier
    resolved_cset_in = (
        construction_set if construction_set is not None else construction_set_identifier
    )
    updated_fields: list[str] = []
    field_checks = (
        ("program_type", resolved_prog_in is not None),
        ("construction_set", resolved_cset_in is not None),
        ("hvac", hvac is not None),
        ("shw", shw is not None),
        ("person_count", person_count is not None),
        ("lighting_watts", lighting_watts is not None),
        ("electric_equipment_watts", electric_equipment_watts is not None),
        ("gas_equipment_watts", gas_equipment_watts is not None),
        ("hot_water_flow", hot_water_flow is not None),
        ("infiltration_ach", infiltration_ach is not None),
        ("daylighting_control", daylighting_control is not None or daylight_center is not None),
        ("window_vent_control", window_vent_control is not None),
        ("window_vent_opening", window_vent_opening is not None),
        ("fans", fans is not None or remove_existing_fans),
        ("process_loads", process_loads is not None or remove_existing_process_loads),
        ("diversify", bool(diversify)),
        ("ceiling_plenum_construction", ceiling_plenum_construction is not None),
        ("floor_plenum_construction", floor_plenum_construction is not None),
        ("construction", construction is not None),
        ("transmittance_schedule", transmittance_schedule is not None),
    )
    for field_name, active in field_checks:
        if active:
            updated_fields.append(field_name)
    if not updated_fields:
        raise ValueError(
            "apply_dragonfly_energy_properties requires at least one Energy property input."
        )

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    if host_target is None or host_target.get("target_type") == "dragonfly_model":
        normalized_target = dict(resolved_model_target)
        host_type = "model"
        host = model
    else:
        normalized_target = normalize_dragonfly_object_target(host_target)
        host_type = normalized_target["object_type"]
        if host_type not in {"room2d", "story", "building", "context_shade"}:
            raise ValueError(
                "apply_dragonfly_energy_properties supports room2d, story, "
                "building, context_shade, and model targets."
            )
        host = _host_from_target(model, normalized_target)

    prog_obj = (
        _resolve_custom_or_standards(
            garden_root,
            resolved_prog_in,
            domain="honeybee_energy",
            object_family="program_type",
            standards_lookup=program_type_by_identifier,
            dict_loader=ProgramType.from_dict,
        )
        if resolved_prog_in is not None
        else None
    )
    cset_obj = (
        _resolve_custom_or_standards(
            garden_root,
            resolved_cset_in,
            domain="honeybee_energy",
            object_family="construction_set",
            standards_lookup=construction_set_by_identifier,
            dict_loader=ConstructionSet.from_dict,
        )
        if resolved_cset_in is not None
        else None
    )
    hvac_obj = _resolve_hvac(garden_root, hvac) if hvac is not None else None
    shw_obj = (
        _resolve_custom_or_standards(
            garden_root,
            shw,
            domain="honeybee_energy",
            object_family="shw_system",
            standards_lookup=None,
            dict_loader=_load_shw_dict,
        )
        if shw is not None
        else None
    )

    affected_room2d_count = 0
    if host_type == "context_shade":
        if construction is not None:
            host.properties.energy.construction = _resolve_custom_or_standards(
                garden_root,
                construction,
                domain="honeybee_energy",
                object_family="construction",
                standards_lookup=shade_construction_by_identifier,
                dict_loader=_load_shade_construction_dict,
            )
        if transmittance_schedule is not None:
            host.properties.energy.transmittance_schedule = _resolve_custom_or_standards(
                garden_root,
                transmittance_schedule,
                domain="honeybee_energy",
                object_family="schedule",
                standards_lookup=schedule_by_identifier,
                dict_loader=dict_to_schedule,
            )
    else:
        rooms = _target_rooms(host, host_type)
        if prog_obj is not None:
            if host_type == "room2d":
                host.properties.energy.program_type = prog_obj
                affected_room2d_count = 1
            elif host_type in {"story", "building"}:
                host.properties.energy.set_all_room_2d_program_type(prog_obj)
                affected_room2d_count = len(rooms)
            else:
                for room in rooms:
                    room.properties.energy.program_type = prog_obj
                affected_room2d_count = len(rooms)
        if cset_obj is not None:
            if host_type in {"room2d", "story", "building"}:
                host.properties.energy.construction_set = cset_obj
            else:
                for bldg in model.buildings:
                    bldg.properties.energy.construction_set = cset_obj
        if hvac_obj is not None:
            if host_type == "building":
                host.properties.energy.set_all_room_2d_hvac(hvac_obj)
            else:
                for room in rooms:
                    room.properties.energy.hvac = hvac_obj.duplicate()
            affected_room2d_count = max(affected_room2d_count, len(rooms))
        if shw_obj is not None:
            if host_type == "building":
                host.properties.energy.set_all_room_2d_shw(shw_obj)
            else:
                for room in rooms:
                    room.properties.energy.shw = shw_obj.duplicate()
            affected_room2d_count = max(affected_room2d_count, len(rooms))
        if ceiling_plenum_construction is not None or floor_plenum_construction is not None:
            target_buildings = (
                [host]
                if host_type == "building"
                else (list(model.buildings) if host_type == "model" else [])
            )
            if not target_buildings:
                raise ValueError(
                    "ceiling_plenum_construction / floor_plenum_construction require building or model target."
                )
            if ceiling_plenum_construction is not None:
                c_plenum = _resolve_custom_or_standards(
                    garden_root,
                    ceiling_plenum_construction,
                    domain="honeybee_energy",
                    object_family="construction",
                    standards_lookup=opaque_construction_by_identifier,
                    dict_loader=dict_to_construction,
                )
                for bldg in target_buildings:
                    bldg.properties.energy.ceiling_plenum_construction = c_plenum
            if floor_plenum_construction is not None:
                f_plenum = _resolve_custom_or_standards(
                    garden_root,
                    floor_plenum_construction,
                    domain="honeybee_energy",
                    object_family="construction",
                    standards_lookup=opaque_construction_by_identifier,
                    dict_loader=dict_to_construction,
                )
                for bldg in target_buildings:
                    bldg.properties.energy.floor_plenum_construction = f_plenum

        for room in rooms:
            re = room.properties.energy
            if person_count is not None:
                re.person_count = float(person_count)
            if lighting_watts is not None:
                re.lighting_watts = float(lighting_watts)
            if electric_equipment_watts is not None:
                re.electric_equipment_watts = float(electric_equipment_watts)
            if gas_equipment_watts is not None:
                re.gas_equipment_watts = float(gas_equipment_watts)
            if hot_water_flow is not None:
                re.hot_water_flow = float(hot_water_flow)
            if infiltration_ach is not None:
                re.infiltration_ach = float(infiltration_ach)
            if daylighting_control is not None:
                re.daylighting_control = _coerce_daylighting_control(daylighting_control, room)
            elif daylight_center is not None:
                re.add_daylight_control_to_center(
                    float(daylight_center["distance_from_floor"]),
                    illuminance_setpoint=float(daylight_center.get("illuminance_setpoint", 300)),
                    control_fraction=float(daylight_center.get("control_fraction", 1)),
                    min_power_input=float(daylight_center.get("min_power_input", 0.3)),
                    min_light_output=float(daylight_center.get("min_light_output", 0.2)),
                    off_at_minimum=bool(daylight_center.get("off_at_minimum", False)),
                    tolerance=float(daylight_center.get("tolerance", 0.01)),
                )
            if window_vent_control is not None:
                re.window_vent_control = _coerce_ventilation_control(window_vent_control)
            if window_vent_opening is not None:
                re.window_vent_opening = _coerce_ventilation_opening(window_vent_opening)
            if remove_existing_fans:
                re.remove_fans()
            if fans is not None:
                for fan_item in fans:
                    fan_obj = _resolve_custom_or_standards(
                        garden_root,
                        fan_item,
                        domain="honeybee_energy",
                        object_family="zone_ventilation_fan",
                        standards_lookup=None,
                        dict_loader=_load_fan_dict,
                    )
                    re.add_fan(fan_obj)
            if remove_existing_process_loads:
                re.remove_process_loads()
            if process_loads is not None:
                for proc_item in process_loads:
                    proc_obj = _resolve_custom_or_standards(
                        garden_root,
                        proc_item,
                        domain="honeybee_energy",
                        object_family="process",
                        standards_lookup=None,
                        dict_loader=_load_process_dict,
                    )
                    re.add_process_load(proc_obj)
        if any(
            val is not None
            for val in (
                person_count,
                lighting_watts,
                electric_equipment_watts,
                gas_equipment_watts,
                hot_water_flow,
                infiltration_ach,
                daylighting_control,
                daylight_center,
                window_vent_control,
                window_vent_opening,
                fans,
                process_loads,
            )
        ) or remove_existing_fans or remove_existing_process_loads:
            affected_room2d_count = max(affected_room2d_count, len(rooms))

        if diversify:
            div_kwargs = dict(diversify) if isinstance(diversify, dict) else {}
            target_buildings = (
                [host]
                if host_type == "building"
                else (list(model.buildings) if host_type == "model" else [])
            )
            if not target_buildings:
                raise ValueError("diversify requires a building or model target.")
            for bldg in target_buildings:
                bldg.properties.energy.diversify(**div_kwargs)
                affected_room2d_count = max(affected_room2d_count, len(bldg.unique_room_2ds))

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
        "identifier": normalized_target.get("object_identifier") or model.identifier,
        "updated_fields": updated_fields,
        "program_type_identifier": program_type_identifier or getattr(prog_obj, "identifier", None),
        "construction_set_identifier": construction_set_identifier or getattr(cset_obj, "identifier", None),
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
                f"{host_type}: {summary_view['identifier']}"
            ),
        ),
    }


def apply_dragonfly_radiance_properties(
    *,
    garden_root: str,
    host_target: dict[str, Any],
    model_target: dict[str, Any] | None = None,
    modifier_set_identifier: str | None = None,
    modifier_set: Any = None,
    modifier: Any = None,
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
    """Apply Radiance properties (standards/Garden library ModifierSet, grids, shade modifier)."""
    resolved_mset_in = modifier_set if modifier_set is not None else modifier_set_identifier
    updated_fields: list[str] = []
    if resolved_mset_in is not None:
        updated_fields.append("modifier_set")
    if modifier is not None:
        updated_fields.append("modifier")
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
    if host_type not in {"room2d", "story", "building", "context_shade"}:
        raise ValueError(
            "apply_dragonfly_radiance_properties supports room2d, story, "
            "building, and context_shade targets."
        )
    if (grid_parameter_type is not None or remove_existing_grid_parameters) and (
        host_type not in {"room2d", "building"}
    ):
        raise ValueError(
            "Dragonfly Radiance grid parameters can be applied to room2d or "
            "building targets."
        )

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(garden_root_path, model_target)
    model = load_dragonfly_model(garden_root_path, resolved_model_target)
    host = _host_from_target(model, normalized_target)

    resolved_modifier_set = (
        _resolve_custom_or_standards(
            garden_root,
            resolved_mset_in,
            domain="honeybee_radiance",
            object_family="modifier_set",
            standards_lookup=modifier_set_by_identifier,
            dict_loader=_load_modifier_set_object,
        )
        if resolved_mset_in is not None
        else None
    )
    resolved_modifier = (
        _resolve_custom_or_standards(
            garden_root,
            modifier,
            domain="honeybee_radiance",
            object_family="modifier",
            standards_lookup=modifier_by_identifier,
            dict_loader=_load_modifier_object,
        )
        if modifier is not None
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
    if host_type == "context_shade":
        if resolved_modifier is not None:
            host.properties.radiance.modifier = resolved_modifier
    else:
        if resolved_modifier_set is not None:
            host.properties.radiance.modifier_set = resolved_modifier_set
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
        "modifier_set_identifier": modifier_set_identifier or getattr(resolved_modifier_set, "identifier", None),
        "modifier_identifier": getattr(resolved_modifier, "identifier", None),
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
    if object_type == "context_shade":
        return _one_by_identifier(
            model.context_shade_by_identifier([identifier]),
            identifier,
            "ContextShade",
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
        "modifier",
        "construction",
        "transmittance_schedule",
        "ceiling_plenum_construction",
        "floor_plenum_construction",
    ):
        value = data.get(key)
        identifier = _identifier(value)
        if identifier is not None:
            fields[key] = identifier
    for scalar_key in (
        "person_count",
        "lighting_watts",
        "electric_equipment_watts",
        "gas_equipment_watts",
        "hot_water_flow",
        "infiltration_ach",
    ):
        if data.get(scalar_key) is not None:
            fields[scalar_key] = data[scalar_key]
    for opt_key in ("daylighting_control", "window_vent_control", "window_vent_opening"):
        if data.get(opt_key) is not None:
            fields[opt_key] = data[opt_key]
    if isinstance(data.get("fans"), list):
        fields["fan_count"] = len(data["fans"])
    if isinstance(data.get("process_loads"), list):
        fields["process_load_count"] = len(data["process_loads"])
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
