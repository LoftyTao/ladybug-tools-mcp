"""Reference analysis for the canonical Ironbug component library."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from garden.ironbug_core.assembly import COMPONENT_LIBRARY_KEY, _component_library


ROOM_SERVING_PREFIXES = ("IB_AirTerminal", "IB_ZoneHVAC")
ROOM_SERVING_CLASSES = {
    "IB_AirLoopHVACUnitarySystem",
    "IB_FanZoneExhaust",
    "IB_NoAirLoop",
    "IB_WaterHeaterHeatPump",
    "IB_WaterHeaterMixed",
    "IB_ZoneEquipmentGroup",
}


@dataclass(frozen=True)
class GraphObject:
    """A compact owner/root description used in search summaries."""

    object_type: str
    identifier: str
    source_class: str
    object_path: str

    def as_dict(self) -> dict[str, str]:
        return {
            "object_type": self.object_type,
            "identifier": self.identifier,
            "source_class": self.source_class,
            "object_path": self.object_path,
        }


@dataclass(frozen=True)
class ComponentRecord:
    identifier: str
    component_type: str
    source_class: str
    data: dict[str, Any]


@dataclass
class ComponentReferenceGraph:
    """Canonical component references, roots, and reachability."""

    records: dict[str, ComponentRecord]
    active_ids: set[str]
    reference_owners: dict[str, list[GraphObject]]
    active_graph_memberships: dict[str, list[GraphObject]]
    roots: tuple[GraphObject, ...]

    @property
    def orphan_ids(self) -> set[str]:
        return set(self.records) - self.active_ids

    def summary(self, identifier: str) -> dict[str, Any]:
        record = self.records[identifier]
        owners = tuple(self.reference_owners.get(identifier, ()))
        memberships = tuple(self.active_graph_memberships.get(identifier, ()))
        return {
            "component_type": record.component_type,
            "source_class": record.source_class,
            "reference_owners": [item.as_dict() for item in owners],
            "active_graph_memberships": [item.as_dict() for item in memberships],
            "is_orphan": identifier not in self.active_ids,
        }


def _payload(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return model_dump(
            by_alias=True,
            exclude_none=True,
            serialize_as_any=True,
        )
    return value


def _source_class(value: Any) -> str:
    payload = _payload(value)
    if isinstance(payload, dict):
        return str(payload.get("type") or payload.get("source_class") or "")
    return str(
        getattr(value, "SOURCE_CLASS", "")
        or getattr(value, "type", "")
        or value.__class__.__name__
    )


def _identifier(value: Any) -> str:
    payload = _payload(value)
    if isinstance(payload, dict):
        return str(payload.get("identifier") or "")
    return str(getattr(value, "identifier", "") or "")


def _field(value: Any, name: str, default: Any = None) -> Any:
    payload = _payload(value)
    if isinstance(payload, dict):
        if name in payload:
            return payload[name]
        return (payload.get("CustomAttributes") or {}).get(name, default)
    return getattr(value, name, default)


def _walk(value: Any) -> Iterable[Any]:
    """Yield nested objects without making library metadata a graph root."""

    value = _payload(value)
    yield value
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "user_data":
                continue
            if isinstance(child, list):
                for item in child:
                    yield from _walk(item)
            elif isinstance(child, dict):
                yield from _walk(child)


def _record_for(value: Any, records: dict[str, ComponentRecord]) -> ComponentRecord | None:
    identifier = _identifier(value)
    if not identifier:
        return None
    return records.get(identifier)


def _direct_component_children(
    value: Any,
    records: dict[str, ComponentRecord],
) -> Iterable[ComponentRecord]:
    """Yield direct canonical children and stop at each canonical boundary."""

    value = _payload(value)
    if isinstance(value, (list, tuple)):
        for item in value:
            child = _record_for(item, records)
            if child is not None:
                yield child
            else:
                yield from _direct_component_children(item, records)
        return
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        if key == "user_data":
            continue
        child = _record_for(item, records)
        if child is not None:
            yield child
        elif isinstance(item, (dict, list, tuple)):
            yield from _direct_component_children(item, records)


def _record_data(record: dict[str, Any], identifier: str) -> ComponentRecord | None:
    if not isinstance(record, dict) or not isinstance(record.get("data"), dict):
        return None
    return ComponentRecord(
        identifier=identifier,
        component_type=str(record.get("component_type") or record.get("source_class") or ""),
        source_class=str(record.get("source_class") or record["data"].get("type") or ""),
        data=record["data"],
    )


def _records(model: Any) -> dict[str, ComponentRecord]:
    library = _component_library(model)
    return {
        str(identifier): component
        for identifier, raw in library.items()
        if (component := _record_data(raw, str(identifier))) is not None
    }


def _is_room_serving(source_class: str) -> bool:
    return source_class in ROOM_SERVING_CLASSES or source_class.startswith(ROOM_SERVING_PREFIXES)


def _as_sequence(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def _has_room_service(value: Any) -> bool:
    if _field(value, "AirTerminal") is not None:
        return True
    for equipment in _as_sequence(_field(value, "ZoneEquipments")):
        if _is_room_serving(_source_class(equipment)) or _source_class(equipment) == "IB_ZoneEquipment":
            return True
    return False


def _has_thermal_zone(value: Any) -> bool:
    if _source_class(value) == "IB_ThermalZone":
        return True
    return any(_source_class(item) == "IB_ThermalZone" for item in _walk(value))


def _root_objects(model: Any, records: dict[str, ComponentRecord]) -> list[tuple[GraphObject, Any]]:
    roots: list[tuple[GraphObject, Any]] = []
    for attr, object_type, path in (
        ("EnergyManagementSystem", "energy_management_system", "EnergyManagementSystem"),
        ("ElectricLoadCenter", "electric_load_center", "ElectricLoadCenter"),
    ):
        value = getattr(model, attr, None)
        if value is not None:
            roots.append(
                (
                    GraphObject(
                        object_type=object_type,
                        identifier=_identifier(value) or path,
                        source_class=_source_class(value),
                        object_path=path,
                    ),
                    value,
                )
            )
    hvac = getattr(model, "HVACSystem", None)
    if hvac is not None:
        for attr, object_type, path_prefix in (
            ("AirLoops", "air_loop", "HVACSystem.AirLoops"),
            ("PlantLoops", "plant_loop", "HVACSystem.PlantLoops"),
            ("VariableRefrigerantFlows", "vrf", "HVACSystem.VariableRefrigerantFlows"),
        ):
            for index, value in enumerate(getattr(hvac, attr, None) or []):
                roots.append(
                    (
                        GraphObject(
                            object_type=object_type,
                            identifier=_identifier(value) or f"{path_prefix}[{index}]",
                            source_class=_source_class(value),
                            object_path=f"{path_prefix}[{index}]",
                        ),
                        value,
                    )
                )
    # Canonical zones can serve independent equipment alongside loop-based systems.
    for identifier, record in records.items():
        if record.source_class == "IB_ThermalZone" and _has_room_service(record.data):
            roots.append(
                (
                    GraphObject(
                        object_type="thermal_zone",
                        identifier=identifier,
                        source_class=record.source_class,
                        object_path=f"user_data.{COMPONENT_LIBRARY_KEY}.{identifier}",
                    ),
                    record.data,
                )
            )
        elif record.source_class == "IB_NoAirLoop" and _has_thermal_zone(record.data):
            roots.append(
                (
                    GraphObject(
                        object_type="no_air_loop",
                        identifier=identifier,
                        source_class=record.source_class,
                        object_path=f"user_data.{COMPONENT_LIBRARY_KEY}.{identifier}",
                    ),
                    record.data,
                )
            )
    # Preserve standalone room-serving objects when no explicit zone was saved.
    if not any(
        root.object_type in {"air_loop", "plant_loop", "vrf", "thermal_zone", "no_air_loop"}
        for root, _ in roots
    ):
        for identifier, record in records.items():
            if _is_room_serving(record.source_class):
                roots.append(
                    (
                        GraphObject(
                            object_type="zone_equipment",
                            identifier=identifier,
                            source_class=record.source_class,
                            object_path=f"user_data.{COMPONENT_LIBRARY_KEY}.{identifier}",
                        ),
                        record.data,
                    )
                )
    return roots


def _append_unique(items: dict[str, list[GraphObject]], identifier: str, value: GraphObject) -> None:
    current = items.setdefault(identifier, [])
    if value not in current:
        current.append(value)


def component_reference_graph(model: Any) -> ComponentReferenceGraph:
    """Analyze component owners and active graph reachability."""

    records = _records(model)
    owners: dict[str, list[GraphObject]] = {}
    memberships: dict[str, list[GraphObject]] = {}
    active_ids: set[str] = set()
    roots = _root_objects(model, records)

    def visit_component(
        identifier: str,
        membership: GraphObject,
        owner: GraphObject | None,
        visiting: set[str],
    ) -> None:
        record = records.get(identifier)
        if record is None:
            return
        active_ids.add(identifier)
        _append_unique(memberships, identifier, membership)
        if owner is not None and not (
            owner.object_type == "component" and owner.identifier == identifier
        ):
            _append_unique(owners, identifier, owner)
        if identifier in visiting:
            return
        next_visiting = {*visiting, identifier}
        for child in _direct_component_children(record.data, records):
            child_owner = GraphObject(
                object_type="component",
                identifier=identifier,
                source_class=record.source_class,
                object_path=f"user_data.{COMPONENT_LIBRARY_KEY}.{identifier}",
            )
            visit_component(child.identifier, membership, child_owner, next_visiting)

    for root, value in roots:
        root_record = _record_for(value, records)
        if root_record is not None:
            visit_component(root_record.identifier, root, None, set())
            continue
        for child in _direct_component_children(value, records):
            visit_component(child.identifier, root, root, set())

    # Reference owners are collected from every canonical record, including orphans.
    for identifier, record in records.items():
        owner = GraphObject(
            object_type="component",
            identifier=identifier,
            source_class=record.source_class,
            object_path=f"user_data.{COMPONENT_LIBRARY_KEY}.{identifier}",
        )
        for child in _direct_component_children(record.data, records):
            if child.identifier != identifier:
                _append_unique(owners, child.identifier, owner)

    return ComponentReferenceGraph(
        records=records,
        active_ids=active_ids,
        reference_owners=owners,
        active_graph_memberships=memberships,
        roots=tuple(root for root, _ in roots),
    )


__all__ = [
    "ComponentRecord",
    "ComponentReferenceGraph",
    "GraphObject",
    "component_reference_graph",
]
