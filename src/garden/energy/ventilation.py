"""Honeybee Energy ventilation and PV-adjacent service helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.model import Model
from honeybee.room import Room
from honeybee_energy.generator.loadcenter import ElectricLoadCenter
from honeybee_energy.generator.pv import PVProperties
from honeybee_energy.ventcool import afn
from honeybee_energy.ventcool.control import VentilationControl
from honeybee_energy.ventcool.fan import VentilationFan
from honeybee_energy.ventcool.opening import VentilationOpening
from honeybee_energy.ventcool.simulation import VentilationSimulationControl

from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report
from garden.honeybee_core.locate import find_object
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
    with_honeybee_model_write_lock,
)
from garden.honeybee_core.targets import normalize_honeybee_object_target
from garden.libraries.properties import save_garden_properties_library_object


def _save_library_result(
    *,
    object_dict: dict[str, Any],
    summary_view: dict[str, Any],
    message: str,
    garden_root: str | None,
    object_family: str,
    ready_for: str,
    return_object_dict: bool,
    identifier: str | None = None,
) -> dict[str, Any]:
    result = {
        "object_dict": object_dict,
        "summary_view": {**summary_view, "ready_for": ready_for},
        "report": make_report(status="ok", message=message),
    }
    if garden_root:
        saved = save_garden_properties_library_object(
            garden_root=garden_root,
            domain="honeybee_energy",
            object_family=object_family,
            object_dict=object_dict,
            identifier=identifier,
        )
        result["target"] = saved["target"]
        result["persistence_receipt"] = saved["persistence_receipt"]
        result["summary_view"]["target"] = saved["target"]
        if not return_object_dict:
            result.pop("object_dict", None)
    return result


def _control_from_fields(
    *,
    min_indoor_temperature: float = -100,
    max_indoor_temperature: float = 100,
    min_outdoor_temperature: float = -100,
    max_outdoor_temperature: float = 100,
    delta_temperature: float = -100,
) -> VentilationControl:
    try:
        return VentilationControl(
            min_indoor_temperature=min_indoor_temperature,
            max_indoor_temperature=max_indoor_temperature,
            min_outdoor_temperature=min_outdoor_temperature,
            max_outdoor_temperature=max_outdoor_temperature,
            delta_temperature=delta_temperature,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid VentilationControl input. {exc}") from exc


def _ventilation_opening_summary(opening: VentilationOpening) -> dict[str, Any]:
    return {
        "type": "VentilationOpening",
        "fraction_area_operable": opening.fraction_area_operable,
        "fraction_height_operable": opening.fraction_height_operable,
        "discharge_coefficient": opening.discharge_coefficient,
        "wind_cross_vent": opening.wind_cross_vent,
        "flow_coefficient_closed": opening.flow_coefficient_closed,
        "flow_exponent_closed": opening.flow_exponent_closed,
        "two_way_threshold": opening.two_way_threshold,
    }


def _ventilation_control_summary(control: VentilationControl) -> dict[str, Any]:
    return {
        "type": "VentilationControl",
        "min_indoor_temperature": control.min_indoor_temperature,
        "max_indoor_temperature": control.max_indoor_temperature,
        "min_outdoor_temperature": control.min_outdoor_temperature,
        "max_outdoor_temperature": control.max_outdoor_temperature,
        "delta_temperature": control.delta_temperature,
        "schedule": control.schedule.identifier if control.schedule else None,
    }


def _zone_ventilation_fan_summary(fan: VentilationFan) -> dict[str, Any]:
    return {
        "type": "VentilationFan",
        "identifier": fan.identifier,
        "flow_rate": fan.flow_rate,
        "ventilation_type": fan.ventilation_type,
        "pressure_rise": fan.pressure_rise,
        "efficiency": fan.efficiency,
        "control": _ventilation_control_summary(fan.control),
    }


def _pv_properties_summary(pv: PVProperties) -> dict[str, Any]:
    return {
        "type": "PVProperties",
        "identifier": pv.identifier,
        "rated_efficiency": pv.rated_efficiency,
        "active_area_fraction": pv.active_area_fraction,
        "module_type": pv.module_type,
        "mounting_type": pv.mounting_type,
        "system_loss_fraction": pv.system_loss_fraction,
        "tracking_ground_coverage_ratio": pv.tracking_ground_coverage_ratio,
    }


def _electric_load_center_summary(load_center: ElectricLoadCenter) -> dict[str, Any]:
    return {
        "type": "ElectricLoadCenter",
        "inverter_efficiency": load_center.inverter_efficiency,
        "inverter_dc_to_ac_size_ratio": load_center.inverter_dc_to_ac_size_ratio,
    }


def create_zone_ventilation_fan(
    *,
    identifier: str,
    flow_rate: float,
    ventilation_type: str = "Balanced",
    pressure_rise: float | None = None,
    efficiency: float | None = None,
    control: dict[str, Any] | None = None,
    min_indoor_temperature: float = -100,
    max_indoor_temperature: float = 100,
    min_outdoor_temperature: float = -100,
    max_outdoor_temperature: float = 100,
    delta_temperature: float = -100,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy zone ventilation fan object."""
    try:
        fan_control = (
            VentilationControl.from_dict(control)
            if control is not None
            else _control_from_fields(
                min_indoor_temperature=min_indoor_temperature,
                max_indoor_temperature=max_indoor_temperature,
                min_outdoor_temperature=min_outdoor_temperature,
                max_outdoor_temperature=max_outdoor_temperature,
                delta_temperature=delta_temperature,
            )
        )
        fan = VentilationFan(
            identifier,
            flow_rate,
            ventilation_type=ventilation_type,
            pressure_rise=pressure_rise,
            efficiency=efficiency,
            control=fan_control,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid zone ventilation fan input. {exc}") from exc
    return _save_library_result(
        object_dict=fan.to_dict(),
        summary_view=_zone_ventilation_fan_summary(fan),
        message=f"Created zone ventilation fan: {fan.identifier}",
        garden_root=garden_root,
        object_family="zone_ventilation_fan",
        ready_for="edit_honeybee_room.zone_ventilation_fans",
        return_object_dict=return_object_dict,
    )


def create_pv_properties(
    *,
    identifier: str,
    rated_efficiency: float = 0.15,
    active_area_fraction: float = 0.9,
    module_type: str | None = None,
    mounting_type: str = "FixedOpenRack",
    system_loss_fraction: float = 0.14,
    tracking_ground_coverage_ratio: float = 0.4,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create Honeybee Energy PVProperties for Shade PV generation."""
    try:
        pv = PVProperties(
            identifier,
            rated_efficiency=rated_efficiency,
            active_area_fraction=active_area_fraction,
            module_type=module_type,
            mounting_type=mounting_type,
            system_loss_fraction=system_loss_fraction,
            tracking_ground_coverage_ratio=tracking_ground_coverage_ratio,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid PVProperties input. {exc}") from exc
    return _save_library_result(
        object_dict=pv.to_dict(),
        summary_view=_pv_properties_summary(pv),
        message=f"Created PVProperties: {pv.identifier}",
        garden_root=garden_root,
        object_family="pv_properties",
        ready_for="edit_honeybee_shade.pv_properties",
        return_object_dict=return_object_dict,
    )


def create_electric_load_center(
    *,
    identifier: str = "electric_load_center",
    inverter_efficiency: float = 0.96,
    inverter_dc_to_ac_size_ratio: float = 1.1,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create Honeybee Energy ElectricLoadCenter model-level PV settings."""
    try:
        load_center = ElectricLoadCenter(
            inverter_efficiency=inverter_efficiency,
            inverter_dc_to_ac_size_ratio=inverter_dc_to_ac_size_ratio,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ElectricLoadCenter input. {exc}") from exc
    return _save_library_result(
        object_dict=load_center.to_dict(),
        summary_view={**_electric_load_center_summary(load_center), "identifier": identifier},
        message=f"Created ElectricLoadCenter: {identifier}",
        garden_root=garden_root,
        object_family="electric_load_center",
        ready_for="edit_honeybee_model.electric_load_center",
        return_object_dict=return_object_dict,
        identifier=identifier,
    )


def _selected_rooms(
    model: Model,
    *,
    room_identifiers: list[str] | None = None,
    room_targets: list[dict[str, Any]] | None = None,
) -> list[Room]:
    rooms: list[Room] = []
    if room_targets:
        for target in room_targets:
            normalized = normalize_honeybee_object_target(target)
            obj = find_object(model, normalized)
            if not isinstance(obj, Room):
                raise ValueError("room_targets must contain Honeybee Room targets.")
            rooms.append(obj)
    if room_identifiers:
        by_id = {room.identifier: room for room in model.rooms}
        for identifier in room_identifiers:
            room = by_id.get(identifier)
            if room is None:
                raise ValueError(f"Room not found: {identifier}")
            if room not in rooms:
                rooms.append(room)
    if not room_targets and not room_identifiers:
        rooms = list(model.rooms)
    if not rooms:
        raise ValueError("No Honeybee Rooms were selected.")
    return rooms


def _save_model_change(
    *,
    garden_root: Path,
    manifest: Any,
    model_target: dict[str, Any],
    model: Model,
    operation: str,
    updated_fields: list[str],
    summary_view: dict[str, Any],
    message: str,
) -> dict[str, Any]:
    updated_model_target, persisted_path = save_honeybee_model(
        garden_root,
        manifest,
        model,
        name=str(model_target["model_identifier"]),
        set_base=manifest.base_model == model_target,
    )
    summary_view = {
        "target": updated_model_target,
        "updated_fields": updated_fields,
        **summary_view,
    }
    return {
        "target": updated_model_target,
        "summary_view": summary_view,
        "persistence_receipt": make_persistence_receipt(
            status="persisted",
            garden_id=manifest.garden_id,
            model_target=updated_model_target,
            persisted_path=persisted_path,
            change_summary={
                "operation": operation,
                "target": updated_model_target,
                "updated_fields": updated_fields,
            },
        ),
        "report": make_report(status="ok", message=message),
    }


@with_honeybee_model_write_lock
def setup_simple_ventilation_properties(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    room_identifiers: list[str] | None = None,
    room_targets: list[dict[str, Any]] | None = None,
    fraction_area_operable: float = 0.5,
    fraction_height_operable: float = 1.0,
    discharge_coefficient: float = 0.45,
    wind_cross_vent: bool = False,
    flow_coefficient_closed: float = 0,
    flow_exponent_closed: float = 0.65,
    two_way_threshold: float = 0.0001,
    min_indoor_temperature: float = -100,
    max_indoor_temperature: float = 100,
    min_outdoor_temperature: float = -100,
    max_outdoor_temperature: float = 100,
    delta_temperature: float = -100,
) -> dict[str, Any]:
    """Apply simple operable-window ventilation properties to selected Rooms."""
    root = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(root, model_target)
    model = load_honeybee_model(root, resolved_model_target)
    rooms = _selected_rooms(
        model,
        room_identifiers=room_identifiers,
        room_targets=room_targets,
    )
    try:
        opening = VentilationOpening(
            fraction_area_operable=fraction_area_operable,
            fraction_height_operable=fraction_height_operable,
            discharge_coefficient=discharge_coefficient,
            wind_cross_vent=wind_cross_vent,
            flow_coefficient_closed=flow_coefficient_closed,
            flow_exponent_closed=flow_exponent_closed,
            two_way_threshold=two_way_threshold,
        )
        control = _control_from_fields(
            min_indoor_temperature=min_indoor_temperature,
            max_indoor_temperature=max_indoor_temperature,
            min_outdoor_temperature=min_outdoor_temperature,
            max_outdoor_temperature=max_outdoor_temperature,
            delta_temperature=delta_temperature,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid simple ventilation properties input. {exc}") from exc

    aperture_count = 0
    for room in rooms:
        room.properties.energy.window_vent_control = control.duplicate()
        room.properties.energy.assign_ventilation_opening(opening.duplicate())
        for aperture in room.apertures:
            aperture.is_operable = True
            aperture.properties.energy.vent_opening = opening.duplicate()
            aperture_count += 1
        for door in room.doors:
            door.properties.energy.vent_opening = opening.duplicate()

    return _save_model_change(
        garden_root=root,
        manifest=manifest,
        model_target=resolved_model_target,
        model=model,
        operation="setup_simple_ventilation_properties",
        updated_fields=["window_vent_control", "vent_opening"],
        summary_view={
            "room_count": len(rooms),
            "aperture_count": aperture_count,
            "ventilation_opening": _ventilation_opening_summary(opening),
            "window_vent_control": _ventilation_control_summary(control),
        },
        message=f"Applied simple ventilation properties to {len(rooms)} room(s).",
    )


@with_honeybee_model_write_lock
def setup_airflow_network(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    room_identifiers: list[str] | None = None,
    room_targets: list[dict[str, Any]] | None = None,
    vent_control_type: str = "MultiZoneWithoutDistribution",
    leakage_type: str = "Medium",
    use_room_infiltration: bool = True,
    atmospheric_pressure: float = 101325,
    delta_pressure: float = 4,
    reference_temperature: float = 20,
    reference_pressure: float = 101325,
    reference_humidity_ratio: float = 0,
    building_type: str = "LowRise",
    long_axis_angle: float = 0,
    aspect_ratio: float = 1,
    autocalculate_geometry_properties: bool = True,
) -> dict[str, Any]:
    """Generate an EnergyPlus AirflowNetwork on selected Honeybee Rooms."""
    root = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(root, model_target)
    model = load_honeybee_model(root, resolved_model_target)
    rooms = _selected_rooms(
        model,
        room_identifiers=room_identifiers,
        room_targets=room_targets,
    )
    try:
        control = VentilationSimulationControl(
            vent_control_type=vent_control_type,
            reference_temperature=reference_temperature,
            reference_pressure=reference_pressure,
            reference_humidity_ratio=reference_humidity_ratio,
            building_type=building_type,
            long_axis_angle=long_axis_angle,
            aspect_ratio=aspect_ratio,
        )
        if autocalculate_geometry_properties:
            control.assign_geometry_properties_from_rooms(rooms)
        model.properties.energy.ventilation_simulation_control = control
        afn.generate(
            rooms,
            leakage_type=leakage_type,
            use_room_infiltration=use_room_infiltration,
            atmospheric_pressure=atmospheric_pressure,
            delta_pressure=delta_pressure,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid airflow network input. {exc}") from exc

    face_crack_count = sum(
        1 for room in rooms for face in room.faces if face.properties.energy.vent_crack is not None
    )
    opening_count = sum(
        1
        for room in rooms
        for obj in [*room.apertures, *room.doors]
        if obj.properties.energy.vent_opening is not None
    )
    return _save_model_change(
        garden_root=root,
        manifest=manifest,
        model_target=resolved_model_target,
        model=model,
        operation="setup_airflow_network",
        updated_fields=["ventilation_simulation_control", "vent_crack", "vent_opening"],
        summary_view={
            "room_count": len(rooms),
            "face_crack_count": face_crack_count,
            "opening_count": opening_count,
            "vent_control_type": control.vent_control_type,
            "leakage_type": leakage_type,
            "use_room_infiltration": use_room_infiltration,
        },
        message=f"Generated AirflowNetwork properties for {len(rooms)} room(s).",
    )
