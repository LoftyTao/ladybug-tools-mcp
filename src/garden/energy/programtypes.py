"""Honeybee Energy program type and load creation services."""

from __future__ import annotations

from typing import Any, TypeVar

from honeybee_energy.lib.programtypes import program_type_by_identifier
from honeybee_energy.lib.schedules import schedule_by_identifier
from honeybee_energy.load.equipment import ElectricEquipment, GasEquipment
from honeybee_energy.load.hotwater import ServiceHotWater
from honeybee_energy.load.infiltration import Infiltration
from honeybee_energy.load.lighting import Lighting
from honeybee_energy.load.people import People
from honeybee_energy.load.setpoint import Setpoint
from honeybee_energy.load.ventilation import Ventilation
from honeybee_energy.programtype import ProgramType
from honeybee_energy.schedule.dictutil import dict_to_schedule
from honeybee_energy.schedule.day import ScheduleDay
from honeybee_energy.schedule.fixedinterval import ScheduleFixedInterval
from honeybee_energy.schedule.ruleset import ScheduleRuleset

from ladybug_tools_mcp.contracts.report import make_report
from garden.libraries.properties import (
    get_garden_properties_library_object,
    save_garden_properties_library_object,
)

EnergySchedule = ScheduleRuleset | ScheduleFixedInterval
LoadT = TypeVar(
    "LoadT",
    People,
    Lighting,
    ElectricEquipment,
    GasEquipment,
    ServiceHotWater,
    Infiltration,
    Ventilation,
    Setpoint,
)


def _unwrap_object_dict(data: Any) -> Any:
    if isinstance(data, dict) and isinstance(data.get("object_dict"), dict):
        return data["object_dict"]
    if isinstance(data, dict) and isinstance(data.get("target"), dict):
        return data["target"]
    return data


def _library_object_dict_from_target(
    *,
    garden_root: str | None,
    data: Any,
    field_name: str,
    domain: str,
    object_family: str,
) -> Any:
    data = _unwrap_object_dict(data)
    if not isinstance(data, dict) or data.get("target_type") != "garden_properties_library_object":
        return data
    if garden_root is None:
        raise ValueError(f"{field_name} target requires garden_root.")
    if data.get("domain") != domain or data.get("object_family") != object_family:
        raise ValueError(f"{field_name} target must reference {domain}:{object_family}.")
    if "path" not in data:
        identifier = data.get("identifier")
        if not identifier:
            raise ValueError(f"{field_name} target requires path or identifier.")
        return get_garden_properties_library_object(
            garden_root=garden_root,
            domain=domain,
            object_family=object_family,
            identifier=str(identifier),
        )["object_dict"]
    return get_garden_properties_library_object(
        garden_root=garden_root,
        target=data,
    )["object_dict"]


def _schedule_from_input(
    data: dict[str, Any] | str | None,
    *,
    field_name: str,
    garden_root: str | None = None,
) -> EnergySchedule | None:
    data = _library_object_dict_from_target(
        garden_root=garden_root,
        data=data,
        field_name=field_name,
        domain="honeybee_energy",
        object_family="schedule",
    )
    if data is None:
        return None
    if isinstance(data, dict) and "type" not in data and isinstance(data.get("identifier"), str):
        data = data["identifier"]
    try:
        if isinstance(data, str):
            return schedule_by_identifier(data)
        if isinstance(data, dict):
            return dict_to_schedule(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid Honeybee Energy schedule. {exc}") from exc
    raise ValueError(f"{field_name} must be a schedule dict or library identifier.")


def _schedule_type_limit_identifier(schedule: EnergySchedule | None) -> str | None:
    if schedule is None or schedule.schedule_type_limit is None:
        return None
    return schedule.schedule_type_limit.identifier


def _validate_people_activity_schedule(schedule: EnergySchedule | None) -> None:
    type_identifier = _schedule_type_limit_identifier(schedule)
    if type_identifier != "Activity Level":
        detail = type_identifier or "none"
        raise ValueError(
            "activity_schedule must use the Activity Level ScheduleTypeLimit "
            f"for People loads; got {detail}. Omit activity_schedule to use "
            "the SDK default seated-activity schedule."
        )


def _load_from_input(
    data: dict[str, Any] | None,
    load_cls: type[LoadT],
    *,
    field_name: str,
    garden_root: str | None = None,
) -> LoadT | None:
    data = _library_object_dict_from_target(
        garden_root=garden_root,
        data=data,
        field_name=field_name,
        domain="honeybee_energy",
        object_family="load",
    )
    if data is None:
        return None
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a {load_cls.__name__} dictionary.")
    if data.get("type") == load_cls.__name__ and "identifier" not in data:
        data = {**data, "identifier": f"custom_{load_cls.__name__.lower()}"}
    if load_cls is People and "type" not in data:
        people_per_area = data.get("people_per_area") or data.get("people_density")
        if people_per_area is not None:
            identifier = str(data.get("identifier") or "custom_people")
            try:
                return People(
                    identifier,
                    float(people_per_area),
                    occupancy_schedule=_schedule_from_input(
                        data.get("occupancy_schedule") or data.get("schedule"),
                        field_name=f"{field_name}.occupancy_schedule",
                        garden_root=garden_root,
                    ),
                    activity_schedule=_schedule_from_input(
                        data.get("activity_schedule"),
                        field_name=f"{field_name}.activity_schedule",
                        garden_root=garden_root,
                    ),
                )
            except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
                raise ValueError(f"{field_name} shorthand must be a valid People input. {exc}") from exc
    if load_cls is Lighting and "type" not in data:
        watts_per_area = (
            data.get("watts_per_area")
            or data.get("_watts_per_area")
            or data.get("power_per_area")
        )
        if watts_per_area is not None:
            identifier = str(data.get("identifier") or data.get("_identifier") or "custom_lighting")
            try:
                return Lighting(
                    identifier,
                    float(watts_per_area),
                    schedule=_schedule_from_input(
                        data.get("schedule") or data.get("schedule_"),
                        field_name=f"{field_name}.schedule",
                        garden_root=garden_root,
                    ),
                )
            except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
                raise ValueError(f"{field_name} shorthand must be a valid Lighting input. {exc}") from exc
    if load_cls is ElectricEquipment and "type" not in data:
        watts_per_area = data.get("watts_per_area") or data.get("power_per_area")
        if watts_per_area is not None:
            identifier = str(data.get("identifier") or "custom_electric_equipment")
            try:
                return ElectricEquipment(
                    identifier,
                    float(watts_per_area),
                    schedule=_schedule_from_input(
                        data.get("schedule"),
                        field_name=f"{field_name}.schedule",
                        garden_root=garden_root,
                    ),
                )
            except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
                raise ValueError(
                    f"{field_name} shorthand must be a valid ElectricEquipment input. {exc}"
                ) from exc
    if load_cls is GasEquipment and "type" not in data:
        watts_per_area = data.get("watts_per_area") or data.get("power_per_area")
        if watts_per_area is not None:
            identifier = str(data.get("identifier") or "custom_gas_equipment")
            try:
                return GasEquipment(
                    identifier,
                    float(watts_per_area),
                    schedule=_schedule_from_input(
                        data.get("schedule"),
                        field_name=f"{field_name}.schedule",
                        garden_root=garden_root,
                    ),
                )
            except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
                raise ValueError(
                    f"{field_name} shorthand must be a valid GasEquipment input. {exc}"
                ) from exc
    if load_cls is ServiceHotWater and "type" not in data:
        flow_per_area = data.get("flow_per_area")
        if flow_per_area is not None:
            identifier = str(data.get("identifier") or "custom_service_hot_water")
            try:
                return ServiceHotWater(
                    identifier,
                    float(flow_per_area),
                    schedule=_schedule_from_input(
                        data.get("schedule"),
                        field_name=f"{field_name}.schedule",
                        garden_root=garden_root,
                    ),
                )
            except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
                raise ValueError(
                    f"{field_name} shorthand must be a valid ServiceHotWater input. {exc}"
                ) from exc
    if load_cls is Infiltration and "type" not in data:
        flow_per_exterior_area = data.get("flow_per_exterior_area")
        if flow_per_exterior_area is not None:
            identifier = str(data.get("identifier") or "custom_infiltration")
            try:
                return Infiltration(
                    identifier,
                    float(flow_per_exterior_area),
                    schedule=_schedule_from_input(
                        data.get("schedule"),
                        field_name=f"{field_name}.schedule",
                        garden_root=garden_root,
                    ),
                )
            except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
                raise ValueError(
                    f"{field_name} shorthand must be a valid Infiltration input. {exc}"
                ) from exc
    if load_cls is Ventilation and "type" not in data:
        ventilation_keys = (
            "flow_per_person",
            "flow_per_area",
            "flow_per_zone",
            "air_changes_per_hour",
        )
        if any(data.get(key) is not None for key in ventilation_keys):
            identifier = str(data.get("identifier") or "custom_ventilation")
            try:
                return Ventilation(
                    identifier,
                    flow_per_person=float(data.get("flow_per_person") or 0),
                    flow_per_area=float(data.get("flow_per_area") or 0),
                    flow_per_zone=float(data.get("flow_per_zone") or 0),
                    air_changes_per_hour=float(data.get("air_changes_per_hour") or 0),
                    schedule=_schedule_from_input(
                        data.get("schedule"),
                        field_name=f"{field_name}.schedule",
                        garden_root=garden_root,
                    ),
                    method=str(data.get("method") or "Sum"),
                )
            except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
                raise ValueError(
                    f"{field_name} shorthand must be a valid Ventilation input. {exc}"
                ) from exc
    if load_cls is Setpoint and "type" not in data:
        if data.get("heating_setpoint") is not None or data.get("cooling_setpoint") is not None:
            identifier = str(data.get("identifier") or "custom_setpoint")
            heating_schedule = data.get("heating_schedule")
            if heating_schedule is None:
                heating_schedule = ScheduleRuleset(
                    f"{identifier}_heating_schedule",
                    ScheduleDay(
                        f"{identifier}_heating_day",
                        [float(data.get("heating_setpoint", 20))],
                    ),
                ).to_dict()
            cooling_schedule = data.get("cooling_schedule")
            if cooling_schedule is None:
                cooling_schedule = ScheduleRuleset(
                    f"{identifier}_cooling_schedule",
                    ScheduleDay(
                        f"{identifier}_cooling_day",
                        [float(data.get("cooling_setpoint", 24))],
                    ),
                ).to_dict()
            try:
                return Setpoint(
                    identifier,
                    _schedule_from_input(
                        heating_schedule,
                        field_name=f"{field_name}.heating_schedule",
                        garden_root=garden_root,
                    ),
                    _schedule_from_input(
                        cooling_schedule,
                        field_name=f"{field_name}.cooling_schedule",
                        garden_root=garden_root,
                    ),
                )
            except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
                raise ValueError(
                    f"{field_name} shorthand must be a valid Setpoint input. {exc}"
                ) from exc
    try:
        load = load_cls.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        if load_cls is Setpoint and data.get("type") == "Setpoint":
            return _setpoint_from_input_dict(data, field_name=field_name)
        raise ValueError(f"{field_name} must be a valid {load_cls.__name__} dictionary. {exc}") from exc
    if not isinstance(load, load_cls):
        raise ValueError(f"{field_name} must resolve to a {load_cls.__name__}.")
    return load


def _setpoint_from_input_dict(data: dict[str, Any], *, field_name: str) -> Setpoint:
    try:
        return Setpoint(
            data["identifier"],
            _schedule_from_input(
                data.get("heating_schedule"),
                field_name=f"{field_name}.heating_schedule",
            ),
            _schedule_from_input(
                data.get("cooling_schedule"),
                field_name=f"{field_name}.cooling_schedule",
            ),
            humidifying_schedule=_schedule_from_input(
                data.get("humidifying_schedule"),
                field_name=f"{field_name}.humidifying_schedule",
            ),
            dehumidifying_schedule=_schedule_from_input(
                data.get("dehumidifying_schedule"),
                field_name=f"{field_name}.dehumidifying_schedule",
            ),
            setpoint_cutout_difference=data.get("setpoint_cutout_difference", 0),
        )
    except Exception as exc:
        raise ValueError(f"{field_name} must be a valid Setpoint dictionary. {exc}") from exc


def _program_type_from_input(
    data: dict[str, Any] | str | None,
    *,
    field_name: str,
    garden_root: str | None = None,
) -> ProgramType | None:
    data = _library_object_dict_from_target(
        garden_root=garden_root,
        data=data,
        field_name=field_name,
        domain="honeybee_energy",
        object_family="program_type",
    )
    if data is None:
        return None
    if isinstance(data, dict) and "type" not in data and isinstance(data.get("identifier"), str):
        data = data["identifier"]
    try:
        if isinstance(data, str):
            return program_type_by_identifier(data)
        if isinstance(data, dict):
            return ProgramType.from_dict(data)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"{field_name} must be a valid Honeybee Energy ProgramType. {exc}") from exc
    raise ValueError(f"{field_name} must be a ProgramType dict or library identifier.")


def _load_summary(load: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    summary = {
        "type": load.__class__.__name__,
        "identifier": load.identifier,
    }
    for field in fields:
        value = getattr(load, field)
        if hasattr(value, "identifier"):
            summary[field] = value.identifier
        elif isinstance(value, str | int | float | bool) or value is None:
            summary[field] = value
        elif hasattr(value, "to_dict"):
            summary[field] = value.to_dict()
        else:
            summary[field] = str(value)
    return summary


def _program_type_summary(program_type: ProgramType) -> dict[str, Any]:
    return {
        "type": "ProgramType",
        "identifier": program_type.identifier,
        "people": program_type.people.identifier if program_type.people else None,
        "lighting": program_type.lighting.identifier if program_type.lighting else None,
        "electric_equipment": (
            program_type.electric_equipment.identifier
            if program_type.electric_equipment
            else None
        ),
        "gas_equipment": program_type.gas_equipment.identifier if program_type.gas_equipment else None,
        "service_hot_water": (
            program_type.service_hot_water.identifier
            if program_type.service_hot_water
            else None
        ),
        "infiltration": program_type.infiltration.identifier if program_type.infiltration else None,
        "ventilation": program_type.ventilation.identifier if program_type.ventilation else None,
        "setpoint": program_type.setpoint.identifier if program_type.setpoint else None,
        "schedule_count": len(program_type.schedules_unique),
    }


def _result(object_dict: dict[str, Any], summary_view: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "object_dict": object_dict,
        "summary_view": summary_view,
        "report": make_report(status="ok", message=message),
    }


def _save_library_result(
    result: dict[str, Any],
    *,
    garden_root: str | None,
    object_family: str,
    ready_for: str,
    return_object_dict: bool,
) -> dict[str, Any]:
    if not garden_root:
        return result
    saved = save_garden_properties_library_object(
        garden_root=garden_root,
        domain="honeybee_energy",
        object_family=object_family,
        object_dict=result["object_dict"],
    )
    result["target"] = saved["target"]
    if object_family in {"load", "program_type", "schedule"}:
        result[f"{object_family}_target"] = saved["target"]
    result["persistence_receipt"] = saved["persistence_receipt"]
    result["summary_view"]["target"] = saved["target"]
    result["summary_view"]["ready_for"] = ready_for
    if not return_object_dict:
        result.pop("object_dict", None)
    return result


def create_people(
    *,
    identifier: str,
    people_per_area: float,
    occupancy_schedule: dict[str, Any] | str | None = None,
    activity_schedule: dict[str, Any] | str | None = None,
    radiant_fraction: float | None = None,
    latent_fraction: float | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy People object."""
    kwargs: dict[str, Any] = {}
    if radiant_fraction is not None:
        kwargs["radiant_fraction"] = radiant_fraction
    if latent_fraction is not None:
        kwargs["latent_fraction"] = latent_fraction
    try:
        occupancy = _schedule_from_input(
            occupancy_schedule,
            field_name="occupancy_schedule",
            garden_root=garden_root,
        )
        activity = _schedule_from_input(
            activity_schedule,
            field_name="activity_schedule",
            garden_root=garden_root,
        )
        if activity_schedule is not None:
            _validate_people_activity_schedule(activity)
        people = People(
            identifier,
            people_per_area,
            occupancy_schedule=occupancy,
            activity_schedule=activity,
            **kwargs,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid People input. {exc}") from exc
    return _save_library_result(
        _result(
        people.to_dict(),
        _load_summary(
            people,
            ("people_per_area", "occupancy_schedule", "activity_schedule", "radiant_fraction", "latent_fraction"),
        ),
        f"Created People: {people.identifier}",
        ),
        garden_root=garden_root,
        object_family="load",
        ready_for="create_program_type.people",
        return_object_dict=return_object_dict,
    )


def create_lighting(
    *,
    identifier: str,
    watts_per_area: float,
    schedule: dict[str, Any] | str | None = None,
    return_air_fraction: float | None = None,
    radiant_fraction: float | None = None,
    visible_fraction: float | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy Lighting object."""
    kwargs: dict[str, Any] = {}
    if return_air_fraction is not None:
        kwargs["return_air_fraction"] = return_air_fraction
    if radiant_fraction is not None:
        kwargs["radiant_fraction"] = radiant_fraction
    if visible_fraction is not None:
        kwargs["visible_fraction"] = visible_fraction
    try:
        lighting = Lighting(
            identifier,
            watts_per_area,
            schedule=_schedule_from_input(schedule, field_name="schedule", garden_root=garden_root),
            **kwargs,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Lighting input. {exc}") from exc
    return _save_library_result(
        _result(
        lighting.to_dict(),
        _load_summary(
            lighting,
            ("watts_per_area", "schedule", "return_air_fraction", "radiant_fraction", "visible_fraction"),
        ),
        f"Created Lighting: {lighting.identifier}",
        ),
        garden_root=garden_root,
        object_family="load",
        ready_for="create_program_type.lighting",
        return_object_dict=return_object_dict,
    )


def create_electric_equipment(
    *,
    identifier: str,
    watts_per_area: float,
    schedule: dict[str, Any] | str | None = None,
    radiant_fraction: float | None = None,
    latent_fraction: float | None = None,
    lost_fraction: float | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy ElectricEquipment object."""
    kwargs: dict[str, Any] = {}
    if radiant_fraction is not None:
        kwargs["radiant_fraction"] = radiant_fraction
    if latent_fraction is not None:
        kwargs["latent_fraction"] = latent_fraction
    if lost_fraction is not None:
        kwargs["lost_fraction"] = lost_fraction
    try:
        equipment = ElectricEquipment(
            identifier,
            watts_per_area,
            schedule=_schedule_from_input(schedule, field_name="schedule", garden_root=garden_root),
            **kwargs,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ElectricEquipment input. {exc}") from exc
    return _save_library_result(
        _result(
        equipment.to_dict(),
        _load_summary(
            equipment,
            ("watts_per_area", "schedule", "radiant_fraction", "latent_fraction", "lost_fraction"),
        ),
        f"Created ElectricEquipment: {equipment.identifier}",
        ),
        garden_root=garden_root,
        object_family="load",
        ready_for="create_program_type.electric_equipment",
        return_object_dict=return_object_dict,
    )


def create_gas_equipment(
    *,
    identifier: str,
    watts_per_area: float,
    schedule: dict[str, Any] | str | None = None,
    radiant_fraction: float | None = None,
    latent_fraction: float | None = None,
    lost_fraction: float | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy GasEquipment object."""
    kwargs: dict[str, Any] = {}
    if radiant_fraction is not None:
        kwargs["radiant_fraction"] = radiant_fraction
    if latent_fraction is not None:
        kwargs["latent_fraction"] = latent_fraction
    if lost_fraction is not None:
        kwargs["lost_fraction"] = lost_fraction
    try:
        equipment = GasEquipment(
            identifier,
            watts_per_area,
            schedule=_schedule_from_input(schedule, field_name="schedule", garden_root=garden_root),
            **kwargs,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid GasEquipment input. {exc}") from exc
    return _save_library_result(
        _result(
        equipment.to_dict(),
        _load_summary(
            equipment,
            ("watts_per_area", "schedule", "radiant_fraction", "latent_fraction", "lost_fraction"),
        ),
        f"Created GasEquipment: {equipment.identifier}",
        ),
        garden_root=garden_root,
        object_family="load",
        ready_for="create_program_type.gas_equipment",
        return_object_dict=return_object_dict,
    )


def create_ventilation(
    *,
    identifier: str,
    flow_per_person: float = 0,
    flow_per_area: float = 0,
    flow_per_zone: float = 0,
    air_changes_per_hour: float = 0,
    schedule: dict[str, Any] | str | None = None,
    method: str = "Sum",
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy Ventilation object."""
    try:
        ventilation = Ventilation(
            identifier,
            flow_per_person=flow_per_person,
            flow_per_area=flow_per_area,
            flow_per_zone=flow_per_zone,
            air_changes_per_hour=air_changes_per_hour,
            schedule=_schedule_from_input(schedule, field_name="schedule", garden_root=garden_root),
            method=method,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Ventilation input. {exc}") from exc
    return _save_library_result(
        _result(
        ventilation.to_dict(),
        _load_summary(
            ventilation,
            ("flow_per_person", "flow_per_area", "flow_per_zone", "air_changes_per_hour", "schedule", "method"),
        ),
        f"Created Ventilation: {ventilation.identifier}",
        ),
        garden_root=garden_root,
        object_family="load",
        ready_for="create_program_type.ventilation or edit_honeybee_room.ventilation",
        return_object_dict=return_object_dict,
    )


def create_infiltration(
    *,
    identifier: str,
    flow_per_exterior_area: float,
    schedule: dict[str, Any] | str | None = None,
    constant_coefficient: float | None = None,
    temperature_coefficient: float | None = None,
    velocity_coefficient: float | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy Infiltration object."""
    kwargs: dict[str, Any] = {}
    if constant_coefficient is not None:
        kwargs["constant_coefficient"] = constant_coefficient
    if temperature_coefficient is not None:
        kwargs["temperature_coefficient"] = temperature_coefficient
    if velocity_coefficient is not None:
        kwargs["velocity_coefficient"] = velocity_coefficient
    try:
        infiltration = Infiltration(
            identifier,
            flow_per_exterior_area,
            schedule=_schedule_from_input(schedule, field_name="schedule", garden_root=garden_root),
            **kwargs,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Infiltration input. {exc}") from exc
    return _save_library_result(
        _result(
        infiltration.to_dict(),
        _load_summary(
            infiltration,
            ("flow_per_exterior_area", "schedule", "constant_coefficient", "temperature_coefficient", "velocity_coefficient"),
        ),
        f"Created Infiltration: {infiltration.identifier}",
        ),
        garden_root=garden_root,
        object_family="load",
        ready_for="create_program_type.infiltration",
        return_object_dict=return_object_dict,
    )


def create_service_hot_water(
    *,
    identifier: str,
    flow_per_area: float,
    schedule: dict[str, Any] | str | None = None,
    target_temperature: float | None = None,
    sensible_fraction: float | None = None,
    latent_fraction: float | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy ServiceHotWater object."""
    kwargs: dict[str, Any] = {}
    if target_temperature is not None:
        kwargs["target_temperature"] = target_temperature
    if sensible_fraction is not None:
        kwargs["sensible_fraction"] = sensible_fraction
    if latent_fraction is not None:
        kwargs["latent_fraction"] = latent_fraction
    try:
        hot_water = ServiceHotWater(
            identifier,
            flow_per_area,
            schedule=_schedule_from_input(schedule, field_name="schedule", garden_root=garden_root),
            **kwargs,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ServiceHotWater input. {exc}") from exc
    return _save_library_result(
        _result(
        hot_water.to_dict(),
        _load_summary(
            hot_water,
            ("flow_per_area", "schedule", "target_temperature", "sensible_fraction", "latent_fraction"),
        ),
        f"Created ServiceHotWater: {hot_water.identifier}",
        ),
        garden_root=garden_root,
        object_family="load",
        ready_for="create_program_type.service_hot_water",
        return_object_dict=return_object_dict,
    )


def create_setpoint(
    *,
    identifier: str = "agent_setpoint",
    heating_schedule: dict[str, Any] | str | None = None,
    cooling_schedule: dict[str, Any] | str | None = None,
    humidifying_schedule: dict[str, Any] | str | None = None,
    dehumidifying_schedule: dict[str, Any] | str | None = None,
    heating_setpoint: float | None = None,
    cooling_setpoint: float | None = None,
    setpoint_cutout_difference: float = 0,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy Setpoint object."""
    if heating_schedule is None:
        if heating_setpoint is None:
            raise ValueError("Provide heating_schedule or heating_setpoint.")
        heating_schedule = ScheduleRuleset(
            f"{identifier}_heating_schedule",
            ScheduleDay(f"{identifier}_heating_day", [heating_setpoint]),
        ).to_dict()
    if cooling_schedule is None:
        if cooling_setpoint is None:
            raise ValueError("Provide cooling_schedule or cooling_setpoint.")
        cooling_schedule = ScheduleRuleset(
            f"{identifier}_cooling_schedule",
            ScheduleDay(f"{identifier}_cooling_day", [cooling_setpoint]),
        ).to_dict()
    try:
        setpoint = Setpoint(
            identifier,
            _schedule_from_input(
                heating_schedule,
                field_name="heating_schedule",
                garden_root=garden_root,
            ),
            _schedule_from_input(
                cooling_schedule,
                field_name="cooling_schedule",
                garden_root=garden_root,
            ),
            humidifying_schedule=_schedule_from_input(
                humidifying_schedule,
                field_name="humidifying_schedule",
                garden_root=garden_root,
            ),
            dehumidifying_schedule=_schedule_from_input(
                dehumidifying_schedule,
                field_name="dehumidifying_schedule",
                garden_root=garden_root,
            ),
            setpoint_cutout_difference=setpoint_cutout_difference,
        )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid Setpoint input. {exc}") from exc
    object_dict = setpoint.to_dict(abridged=False)
    result = _result(
        object_dict,
        _load_summary(
            setpoint,
            ("heating_schedule", "cooling_schedule", "humidifying_schedule", "dehumidifying_schedule", "setpoint_cutout_difference"),
        ),
        f"Created Setpoint: {setpoint.identifier}",
    )
    return _save_library_result(
        result,
        garden_root=garden_root,
        object_family="load",
        ready_for="create_program_type.setpoint or edit_honeybee_room.setpoint",
        return_object_dict=return_object_dict,
    )


def create_program_type(
    *,
    identifier: str,
    base_program_type: dict[str, Any] | str | None = None,
    people: dict[str, Any] | None = None,
    lighting: dict[str, Any] | None = None,
    electric_equipment: dict[str, Any] | None = None,
    gas_equipment: dict[str, Any] | None = None,
    service_hot_water: dict[str, Any] | None = None,
    infiltration: dict[str, Any] | None = None,
    ventilation: dict[str, Any] | None = None,
    setpoint: dict[str, Any] | None = None,
    garden_root: str | None = None,
    return_object_dict: bool = True,
) -> dict[str, Any]:
    """Create a Honeybee Energy ProgramType object."""
    base = _program_type_from_input(
        base_program_type,
        field_name="base_program_type",
        garden_root=garden_root,
    )
    components = {
        "people": base.people if base else None,
        "lighting": base.lighting if base else None,
        "electric_equipment": base.electric_equipment if base else None,
        "gas_equipment": base.gas_equipment if base else None,
        "service_hot_water": base.service_hot_water if base else None,
        "infiltration": base.infiltration if base else None,
        "ventilation": base.ventilation if base else None,
        "setpoint": base.setpoint if base else None,
    }
    if people is not None:
        components["people"] = _load_from_input(
            people,
            People,
            field_name="people",
            garden_root=garden_root,
        )
    if lighting is not None:
        components["lighting"] = _load_from_input(
            lighting,
            Lighting,
            field_name="lighting",
            garden_root=garden_root,
        )
    if electric_equipment is not None:
        components["electric_equipment"] = _load_from_input(
            electric_equipment,
            ElectricEquipment,
            field_name="electric_equipment",
            garden_root=garden_root,
        )
    if gas_equipment is not None:
        components["gas_equipment"] = _load_from_input(
            gas_equipment,
            GasEquipment,
            field_name="gas_equipment",
            garden_root=garden_root,
        )
    if service_hot_water is not None:
        components["service_hot_water"] = _load_from_input(
            service_hot_water,
            ServiceHotWater,
            field_name="service_hot_water",
            garden_root=garden_root,
        )
    if infiltration is not None:
        components["infiltration"] = _load_from_input(
            infiltration,
            Infiltration,
            field_name="infiltration",
            garden_root=garden_root,
        )
    if ventilation is not None:
        components["ventilation"] = _load_from_input(
            ventilation,
            Ventilation,
            field_name="ventilation",
            garden_root=garden_root,
        )
    if setpoint is not None:
        components["setpoint"] = _load_from_input(
            setpoint,
            Setpoint,
            field_name="setpoint",
            garden_root=garden_root,
        )
    try:
        program_type = ProgramType(identifier, **components)
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid ProgramType input. {exc}") from exc
    return _save_library_result(
        _result(
            program_type.to_dict(),
            _program_type_summary(program_type),
            f"Created ProgramType: {program_type.identifier}",
        ),
        garden_root=garden_root,
        object_family="program_type",
        ready_for="edit_honeybee_room.program_type",
        return_object_dict=return_object_dict,
    )
