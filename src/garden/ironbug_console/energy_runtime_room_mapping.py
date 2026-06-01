"""Room-assignment preflight for DetailedHVAC Python Console runs."""

from __future__ import annotations

from typing import Any, Mapping

from honeybee_energy.hvac.detailed import DetailedHVAC


UNITARY_CONTROL_ZONE_SOURCE_CLASSES = {
    "IB_AirLoopHVACUnitarySystem",
    "IB_AirLoopHVACUnitaryHeatPumpAirToAir",
    "IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed",
}


def _detailed_hvac_room_mapping_issues(
    hvac: DetailedHVAC,
    *,
    assigned_room_ids: set[str],
) -> list[dict[str, Any]]:
    """Check only room assignment invariants before the generic writer path."""

    unsupported: list[dict[str, Any]] = []
    seen_room_ids: set[str] = set()
    for thermal_zone in _iter_thermal_zone_specs(hvac.specification):
        room_id = _thermal_zone_name(thermal_zone)
        if room_id is not None and room_id in seen_room_ids:
            unsupported.append(
                {
                    "room_identifier": room_id,
                    "detailed_hvac_identifier": hvac.identifier,
                    "reason": "duplicate_thermal_zone_room",
                }
            )
            continue
        if room_id is not None:
            seen_room_ids.add(room_id)
        if room_id not in assigned_room_ids:
            unsupported.append(
                {
                    "room_identifier": room_id,
                    "detailed_hvac_identifier": hvac.identifier,
                    "reason": "unassigned_thermal_zone_room",
                }
            )
            continue
    missing_room_ids = sorted(assigned_room_ids - seen_room_ids)
    if missing_room_ids:
        unsupported.append(
            {
                "room_identifier": None,
                "detailed_hvac_identifier": hvac.identifier,
                "reason": "missing_assigned_room_thermal_zones",
                "missing_room_identifiers": missing_room_ids,
            }
        )
    return unsupported


def _iter_thermal_zone_specs(value: Any) -> list[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        source_class = _source_class(value)
        if source_class == "IB_ThermalZone":
            return [value]
        zones: list[Mapping[str, Any]] = []
        for key, item in value.items():
            if (
                source_class in UNITARY_CONTROL_ZONE_SOURCE_CLASSES
                and key in {
                    "Children",
                    "ControlZone",
                    "ControllingZone",
                    "ControllingZoneOrThermostatLocation",
                }
            ):
                continue
            zones.extend(_iter_thermal_zone_specs(item))
        return zones
    if isinstance(value, list | tuple):
        zones: list[Mapping[str, Any]] = []
        for item in value:
            zones.extend(_iter_thermal_zone_specs(item))
        return zones
    return []


def _source_class(value: Mapping[str, Any]) -> str | None:
    source_type = value.get("$type") or value.get("type")
    if not isinstance(source_type, str) or not source_type:
        return None
    return source_type.split(",", 1)[0].rsplit(".", 1)[-1]


def _thermal_zone_name(thermal_zone: Mapping[str, Any]) -> str | None:
    for attribute in thermal_zone.get("CustomAttributes") or []:
        field = attribute.get("Field") or {}
        if field.get("FullName") == "Name":
            value = attribute.get("Value")
            return str(value) if value is not None else None
    identifier = thermal_zone.get("identifier")
    return str(identifier) if identifier is not None else None
