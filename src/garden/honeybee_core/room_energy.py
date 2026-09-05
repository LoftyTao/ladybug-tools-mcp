"""Atomic batch assignment of Honeybee Room Energy properties."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from honeybee.model import Model
from honeybee.room import Room

from garden.operations import (
    GardenRevisionConflictError,
    active_operation_controls,
)
from garden.honeybee_core.edit import (
    _construction_set_from_input,
    _hvac_from_dict,
    _library_object_dict_from_target,
    _parse_zone_ventilation_fan_update,
    _program_type_from_input,
    _setpoint_from_dict,
    _ventilation_from_dict,
    _zone_ventilation_fan_from_dict,
)
from garden.honeybee_core.geometry import validate_honeybee_room
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    save_honeybee_model,
)
from garden.honeybee_core.targets import (
    make_honeybee_object_target,
    normalize_honeybee_object_target,
)
from ladybug_tools_mcp.contracts.receipts import make_persistence_receipt
from ladybug_tools_mcp.contracts.report import make_report


_ENERGY_FIELDS = (
    "program_type",
    "construction_set",
    "hvac",
    "ventilation",
    "setpoint",
    "zone_ventilation_fans",
)
_ENERGY_FIELD_SET = set(_ENERGY_FIELDS)
_MAX_IDENTIFIER_SAMPLE = 5


def apply_room_energy_properties(
    *,
    garden_root: str,
    energy_properties: dict[str, Any],
    room_targets: list[dict[str, Any]] | None = None,
    room_identifiers: list[str] | None = None,
    model_target: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one shared Honeybee Energy property change to multiple Rooms."""
    room_inputs = _validate_room_inputs(room_targets, room_identifiers)
    property_inputs = _resolve_energy_properties(garden_root, energy_properties)

    garden_root_path = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(
        garden_root_path,
        model_target,
    )
    model = load_honeybee_model(garden_root_path, resolved_model_target)
    room_targets = _resolve_rooms(
        room_inputs,
        manifest.garden_id,
        str(resolved_model_target["model_identifier"]),
        model,
        allow_identifiers=room_identifiers is not None,
    )

    # Validate every selected Room before mutating the working copy.
    rooms_by_identifier = {room.identifier: room for room in model.rooms}
    for target in room_targets:
        validate_honeybee_room(rooms_by_identifier[target["object_identifier"]])

    working_model = model.duplicate()
    working_rooms = {room.identifier: room for room in working_model.rooms}
    updated_room_identifiers: list[str] = []
    for target in room_targets:
        room = working_rooms[target["object_identifier"]]
        if _apply_properties(room, property_inputs):
            updated_room_identifiers.append(room.identifier)
        validate_honeybee_room(room)

    room_identifiers = [target["object_identifier"] for target in room_targets]
    sample = room_identifiers[:_MAX_IDENTIFIER_SAMPLE]
    updated_sample = updated_room_identifiers[:_MAX_IDENTIFIER_SAMPLE]
    updated_fields = list(property_inputs)
    controls = active_operation_controls()
    change_summary = {
        "operation": "apply_room_energy_properties",
        "target": resolved_model_target,
        "updated_fields": updated_fields,
        "requested_room_count": len(room_inputs),
        "room_count": len(room_targets),
        "updated_room_count": len(updated_room_identifiers),
        "room_identifiers_sample": sample,
        "updated_room_identifiers_sample": updated_sample,
    }

    if updated_room_identifiers:
        updated_model_target, persisted_path = save_honeybee_model(
            garden_root_path,
            manifest,
            working_model,
            name=str(resolved_model_target["model_identifier"]),
            set_base=manifest.base_honeybee_model == resolved_model_target,
        )
        receipt_status = "persisted"
    else:
        updated_model_target = resolved_model_target
        persisted_path = str(resolved_model_target.get("path", ""))
        receipt_status = "no_change"
        if controls is not None and controls[1] is not None:
            expected_revision = controls[1]
            if expected_revision != manifest.revision:
                raise GardenRevisionConflictError(
                    expected_revision=expected_revision,
                    current_revision=manifest.revision,
                )

    change_summary["model_target"] = updated_model_target
    response = {
        "target": updated_model_target,
        "model_target": updated_model_target,
        "summary_view": {
            "model_target": updated_model_target,
            "room_count": len(room_targets),
            "requested_room_count": len(room_inputs),
            "updated_room_count": len(updated_room_identifiers),
            "updated_fields": updated_fields,
            "room_identifiers_sample": sample,
            "updated_room_identifiers_sample": updated_sample,
        },
        "persistence_receipt": make_persistence_receipt(
            status=receipt_status,
            garden_id=manifest.garden_id,
            base_honeybee_model_changed=(
                receipt_status == "persisted"
                and manifest.base_honeybee_model == resolved_model_target
            ),
            model_target=updated_model_target,
            persisted_path=persisted_path,
            change_summary=change_summary,
        ),
        "report": make_report(
            status="ok",
            message=(
                f"Applied Honeybee Energy properties to "
                f"{len(updated_room_identifiers)} of {len(room_targets)} Room(s)."
                if receipt_status == "persisted"
                else "Honeybee Room Energy properties already match the requested values."
            ),
        ),
    }
    if receipt_status == "no_change":
        response["runtime_status"] = "no_change"
    return response


def _validate_room_inputs(
    room_targets: list[dict[str, Any]] | None,
    room_identifiers: list[str] | None,
) -> list[Any]:
    if (room_targets is None) == (room_identifiers is None):
        raise ValueError("Provide exactly one of room_targets or room_identifiers.")
    values: list[Any] = (
        room_targets if room_targets is not None else room_identifiers or []
    )
    if not isinstance(values, list) or not values:
        raise ValueError("Room target or identifier collection must not be empty.")
    return values


def _resolve_rooms(
    values: list[Any],
    garden_id: str,
    model_identifier: str,
    model: Model,
    *,
    allow_identifiers: bool,
) -> list[dict[str, Any]]:
    rooms_by_identifier = {room.identifier: room for room in model.rooms}
    resolved: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, value in enumerate(values):
        if isinstance(value, str):
            if not allow_identifiers:
                raise ValueError(
                    f"room_targets[{index}] must be a Honeybee Room target dict."
                )
            identifier = value
            if not identifier.strip():
                raise ValueError(f"room_identifiers[{index}] must not be empty.")
            if identifier not in rooms_by_identifier:
                raise ValueError(f"Honeybee Room not found: {identifier}")
            target = make_honeybee_object_target(
                garden_id=garden_id,
                model_identifier=model_identifier,
                object_type="room",
                object_identifier=identifier,
            )
        else:
            if allow_identifiers:
                raise ValueError(f"room_identifiers[{index}] must be a string.")
            try:
                target = normalize_honeybee_object_target(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"room_targets[{index}] must be a Honeybee Room target.") from exc
            if target.get("object_type") != "room":
                raise ValueError(f"room_targets[{index}] must identify a Honeybee Room.")
            if target.get("garden_id") != garden_id:
                raise ValueError(
                    f"room_targets[{index}] belongs to a different Garden."
                )
            if target.get("model_identifier") != model_identifier:
                raise ValueError(
                    f"room_targets[{index}] belongs to Honeybee model "
                    f"{target.get('model_identifier')!r}, expected {model_identifier!r}."
                )
            identifier = str(target["object_identifier"])
            if identifier not in rooms_by_identifier:
                raise ValueError(f"Honeybee Room not found: {identifier}")

        if identifier in seen:
            continue
        seen.add(identifier)
        resolved.append(target)
    return resolved


def _resolve_energy_properties(
    garden_root: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(data, dict) or not data:
        raise ValueError("energy_properties must contain at least one supported field.")
    unknown = sorted(set(data) - _ENERGY_FIELD_SET)
    if unknown:
        raise ValueError(
            "energy_properties contains unsupported field(s): "
            f"{', '.join(unknown)}. Supported fields: {', '.join(_ENERGY_FIELDS)}."
        )

    resolved: dict[str, Any] = {}
    for field in _ENERGY_FIELDS:
        if field not in data:
            continue
        value = data[field]
        if value is None:
            raise ValueError(f"energy_properties.{field} must not be null.")
        if field == "program_type":
            value = _library_object_dict_from_target(
                garden_root=Path(garden_root).expanduser().resolve(),
                data=value,
                field_name=field,
                domain="honeybee_energy",
                object_family="program_type",
            )
            resolved[field] = _program_type_from_input(value)
        elif field == "construction_set":
            value = _library_object_dict_from_target(
                garden_root=Path(garden_root).expanduser().resolve(),
                data=value,
                field_name=field,
                domain="honeybee_energy",
                object_family="construction_set",
            )
            resolved[field] = _construction_set_from_input(value)
        elif field == "hvac":
            value = _library_object_dict_from_target(
                garden_root=Path(garden_root).expanduser().resolve(),
                data=value,
                field_name=field,
                domain="honeybee_energy",
                object_family="hvac",
            )
            resolved[field] = _hvac_from_dict(value)
        elif field == "ventilation":
            value = _library_object_dict_from_target(
                garden_root=Path(garden_root).expanduser().resolve(),
                data=value,
                field_name=field,
                domain="honeybee_energy",
                object_family="load",
            )
            resolved[field] = _ventilation_from_dict(value)
        elif field == "setpoint":
            value = _library_object_dict_from_target(
                garden_root=Path(garden_root).expanduser().resolve(),
                data=value,
                field_name=field,
                domain="honeybee_energy",
                object_family="load",
            )
            resolved[field] = _setpoint_from_dict(value)
        else:
            operation, fan_inputs = _parse_zone_ventilation_fan_update(value)
            fans = []
            for fan_input in fan_inputs:
                fan_input = _library_object_dict_from_target(
                    garden_root=Path(garden_root).expanduser().resolve(),
                    data=fan_input,
                    field_name=field,
                    domain="honeybee_energy",
                    object_family="zone_ventilation_fan",
                )
                fans.append(_zone_ventilation_fan_from_dict(fan_input))
            resolved[field] = {"operation": operation, "fans": fans}
    return resolved


def _apply_properties(room: Room, properties: dict[str, Any]) -> bool:
    changed = False
    energy = room.properties.energy
    for field, value in properties.items():
        if field == "zone_ventilation_fans":
            changed = _apply_fans(energy, value) or changed
            continue
        current = getattr(energy, field)
        if _serialized(current) == _serialized(value):
            continue
        setattr(energy, field, _duplicate(value))
        changed = True
    return changed


def _apply_fans(energy: Any, update: dict[str, Any]) -> bool:
    operation = update["operation"]
    fans = list(energy.fans or [])
    if operation == "clear":
        if not fans:
            return False
        energy.remove_fans()
        return True

    desired = update["fans"]
    if operation == "replace_all":
        if [_serialized(fan) for fan in fans] == [_serialized(fan) for fan in desired]:
            return False
        energy.remove_fans()
        for fan in desired:
            energy.add_fan(_duplicate(fan))
        return True

    existing_by_identifier = {str(fan.identifier): fan for fan in fans}
    pending: dict[str, Any] = {}
    for fan in desired:
        identifier = str(fan.identifier)
        existing = existing_by_identifier.get(identifier) or pending.get(identifier)
        if existing is not None:
            if _serialized(existing) != _serialized(fan):
                raise ValueError(
                    "zone_ventilation_fans.add contains a conflicting fan "
                    f"identifier: {identifier}."
                )
            continue
        pending[identifier] = fan
    for fan in pending.values():
        energy.add_fan(_duplicate(fan))
    return bool(pending)


def _duplicate(value: Any) -> Any:
    duplicate = getattr(value, "duplicate", None)
    return duplicate() if callable(duplicate) else value


def _serialized(value: Any) -> Any:
    to_dict = getattr(value, "to_dict", None)
    return to_dict() if callable(to_dict) else value
