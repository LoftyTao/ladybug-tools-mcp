"""Honeybee Energy daylighting control service helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from garden.energy.ventilation import _save_model_change, _selected_rooms
from garden.honeybee_core.model_io import (
    load_honeybee_model,
    resolve_model_target,
    with_honeybee_model_write_lock,
)


def _daylighting_control_summary(control: Any) -> dict[str, Any]:
    return {
        "type": "DaylightingControl",
        "sensor_position": control.sensor_position.to_dict(),
        "illuminance_setpoint": control.illuminance_setpoint,
        "control_fraction": control.control_fraction,
        "min_power_input": control.min_power_input,
        "min_light_output": control.min_light_output,
        "off_at_minimum": control.off_at_minimum,
    }


@with_honeybee_model_write_lock
def setup_daylighting_control_to_center(
    *,
    garden_root: str,
    model_target: dict[str, Any] | None = None,
    room_identifiers: list[str] | None = None,
    room_targets: list[dict[str, Any]] | None = None,
    distance_from_floor: float = 0.8,
    illuminance_setpoint: float = 300,
    control_fraction: float = 1.0,
    min_power_input: float = 0.3,
    min_light_output: float = 0.2,
    off_at_minimum: bool = False,
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Assign Honeybee Energy daylighting controls near selected Room centers."""
    root = Path(garden_root).expanduser().resolve()
    manifest, resolved_model_target = resolve_model_target(root, model_target)
    model = load_honeybee_model(root, resolved_model_target)
    rooms = _selected_rooms(
        model,
        room_identifiers=room_identifiers,
        room_targets=room_targets,
    )

    controls: list[dict[str, Any]] = []
    skipped_rooms: list[str] = []
    try:
        for room in rooms:
            control = room.properties.energy.add_daylight_control_to_center(
                distance_from_floor=distance_from_floor,
                illuminance_setpoint=illuminance_setpoint,
                control_fraction=control_fraction,
                min_power_input=min_power_input,
                min_light_output=min_light_output,
                off_at_minimum=off_at_minimum,
                tolerance=tolerance,
            )
            if control is None:
                skipped_rooms.append(room.identifier)
            else:
                controls.append(
                    {
                        "room_identifier": room.identifier,
                        **_daylighting_control_summary(control),
                    }
                )
    except Exception as exc:  # pragma: no cover - SDK-raised diagnostics
        raise ValueError(f"Invalid daylighting control input. {exc}") from exc

    if not controls:
        raise ValueError(
            "No daylighting controls were assigned. Check room height, floor geometry, "
            "and distance_from_floor."
        )

    return _save_model_change(
        garden_root=root,
        manifest=manifest,
        model_target=resolved_model_target,
        model=model,
        operation="setup_daylighting_control_to_center",
        updated_fields=["daylighting_control"],
        summary_view={
            "room_count": len(rooms),
            "control_count": len(controls),
            "controls": controls,
            "skipped_rooms": skipped_rooms,
        },
        message=f"Assigned daylighting controls to {len(controls)} room(s).",
    )
