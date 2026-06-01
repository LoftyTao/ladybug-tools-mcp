"""Field and identifier extraction for Ironbug Console graph decoding."""

from __future__ import annotations

import re
from typing import Any, Mapping

_STRUCTURAL_KEYS = frozenset(
    {
        "$type",
        "type",
        "AirLoops",
        "PlantLoops",
        "VariableRefrigerantFlows",
        "ThermalZones",
        "ZoneEquipments",
        "Children",
        "SupplyComponents",
        "DemandComponents",
        "Branches",
        "Terminals",
        "Stages",
        "OAStreamObjs",
        "ReliefStreamObjs",
        "SizingZone",
        "AirTerminal",
        "SupplyPlenum",
        "ReturnPlenum",
        "ElectricalStorage",
        "StorageConverter",
        "CustomAttributes",
        "CustomOutputVariables",
        "IBProperties",
    }
)
_TRACKING_ID_RE = re.compile(r"TrackingID:#\[(?P<identifier>[^\]]+)\]")


def _source_class(value: Mapping[str, Any]) -> str | None:
    source_type = value.get("$type") or value.get("type")
    if not isinstance(source_type, str) or not source_type:
        return None
    return source_type.split(",", 1)[0].rsplit(".", 1)[-1]


def _fields(value: Mapping[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    custom_attributes = value.get("CustomAttributes")
    if isinstance(custom_attributes, list):
        for attribute in custom_attributes:
            if not isinstance(attribute, Mapping):
                continue
            field = attribute.get("Field")
            if not isinstance(field, Mapping):
                continue
            full_name = field.get("FullName")
            if full_name:
                fields[str(full_name)] = attribute.get("Value")
    for key, item in value.items():
        if key in _STRUCTURAL_KEYS or item is None:
            continue
        if isinstance(item, str | int | float | bool):
            fields[str(key)] = item
    ib_properties = value.get("IBProperties")
    if isinstance(ib_properties, Mapping):
        for key, item in ib_properties.items():
            if key == "$type" or item is None:
                continue
            if isinstance(item, str | int | float | bool):
                fields.setdefault(str(key), item)
    return fields


def _identifier(
    value: Mapping[str, Any],
    fields: Mapping[str, Any],
    source_class: str,
    state: Any,
) -> str:
    for candidate in (
        value.get("identifier"),
        value.get("id"),
        _tracking_identifier(fields.get("Comment")),
        fields.get("Name"),
    ):
        if candidate:
            return str(candidate)
    return state.next_identifier(source_class)


def _tracking_identifier(comment: Any) -> str | None:
    if not isinstance(comment, str):
        return None
    match = _TRACKING_ID_RE.search(comment)
    if match is None:
        return None
    return match.group("identifier")
