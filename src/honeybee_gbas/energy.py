"""Source construction, material and room program translation for native DWG properties."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from typing import Sequence

from honeybee.units import conversion_factor_to_meters
from honeybee_energy.construction.dynamic import WindowConstructionDynamic
from honeybee_energy.construction.opaque import OpaqueConstruction
from honeybee_energy.construction.window import WindowConstruction
from honeybee_energy.construction.windowshade import WindowConstructionShade
from honeybee_energy.material.opaque import EnergyMaterial, EnergyMaterialNoMass, EnergyMaterialVegetation
from honeybee_energy.programtype import ProgramType

from . import model as hb


@dataclass(frozen=True)
class NativeConstructionPlan:
    materials: tuple[dict, ...]
    constructions: tuple[dict, ...]
    assignments: dict[str, int]
    excluded: tuple[dict, ...]
    role_assignments: dict[str, dict[str, int]]


def node(key, properties=(), children=()):
    return {"key": key, "properties": list(properties), "children": list(children)}


def collection(key, items):
    return node(key, [("ItemCnt", 0, len(items))], [dict(item, key=f"Item{index}") for index, item in enumerate(items)])


def group(key, name, items):
    return node(key, [("Name", 2, name), ("Type", 0, 2)], [collection("SubItems", items)])


def construction_category(component):
    kind = type(component).__name__
    exterior = str(component.boundary_condition) in {"Outdoors", "Ground"}
    if kind == "Aperture":
        if str(component.parent.type) == "RoofCeiling":
            return "天窗"
        return "外窗" if exterior else "内窗"
    if kind == "Door":
        return "外门" if exterior else "内门"
    face_type = str(component.type)
    if face_type == "Wall":
        if str(component.boundary_condition) == "Ground":
            return "地下墙"
        return "外墙" if exterior else "内墙"
    if face_type == "RoofCeiling":
        return "屋顶"
    if face_type == "Floor":
        return "楼板"
    return None


def plan_constructions(model, native_roles=None):
    candidates = {}
    excluded = []
    for room in model.rooms:
        for face in room.faces:
            for component in (face, *face.apertures, *face.doors):
                category = construction_category(component)
                if category is None:
                    excluded.append({"identifier": component.identifier, "reason": "native_boundary_semantics", "kind": str(face.type)})
                    continue
                construction = component.properties.energy.construction
                opening = component is not face
                properties = hb.thermal_properties(component) if opening else None
                u_factor = float(properties.u_factor(model.units) if opening else construction.u_factor)
                glazed = isinstance(construction, (WindowConstruction, WindowConstructionShade, WindowConstructionDynamic))
                shgc = float(properties.shgc(model.units)) if opening and glazed else None
                key = (category, json.dumps(construction.to_dict(), sort_keys=True), round(u_factor, 8), round(shgc, 8) if shgc is not None else None)
                if key not in candidates:
                    candidates[key] = {"construction": construction, "category": category, "u_factor": u_factor, "shgc": shgc, "sources": [], "boundaries": set()}
                candidates[key]["sources"].append(component.identifier)
                candidates[key]["boundaries"].add(str(component.boundary_condition))
    materials = []
    material_ids = {}
    constructions = []
    assignments = {}
    for index, (_, candidate) in enumerate(sorted(candidates.items()), 100001):
        construction = candidate["construction"]
        layers = []
        unsupported = []
        if isinstance(construction, OpaqueConstruction):
            for material in construction.materials:
                massless = isinstance(material, EnergyMaterialNoMass)
                if not isinstance(material, (EnergyMaterial, EnergyMaterialNoMass, EnergyMaterialVegetation)):
                    unsupported.append({"identifier": material.identifier, "type": type(material).__name__})
                    continue
                key = json.dumps(material.to_dict(), sort_keys=True)
                if key not in material_ids:
                    identity = 100001 + len(materials)
                    material_ids[key] = identity
                    record = {
                        "id": identity, "identifier": material.identifier,
                        "name": material.display_name or material.identifier,
                        "conductivity": 0.0 if massless else float(material.conductivity),
                        "density": 0.0 if massless else float(material.density),
                        "specific_heat": 0.0 if massless else float(material.specific_heat),
                        "heat_storage_coefficient": 0.0 if massless else math.sqrt(2.0 * math.pi * material.conductivity * material.density * material.specific_heat / 86400.0),
                        "thickness_mm": 0.0 if massless else float(material.thickness) * 1000.0,
                        "solar_absorptance": float(material.solar_absorptance),
                        "thermal_absorptance": float(material.thermal_absorptance),
                    }
                    if massless:
                        record.update(native_material_type=2, r_value=float(material.r_value),
                                      source_type="EnergyMaterialNoMass", mapping="native_equivalent_thermal_resistance")
                    elif isinstance(material, EnergyMaterialVegetation):
                        record.update(source_type="EnergyMaterialVegetation", mapping="SDK_soil_layer_thermal_properties",
                                      vegetation_energy_processes="outside_native_material_intersection")
                    materials.append(record)
                layers.append({"material_id": material_ids[key], "thickness_mm": 0.0 if massless else float(material.thickness) * 1000.0})
        mode = "source_material_layers_and_u_factor" if isinstance(construction, OpaqueConstruction) and not unsupported else "sdk_equivalent_thermal_properties"
        record = {"id": index, "identifier": construction.identifier, "name": construction.display_name or construction.identifier,
                  "category": candidate["category"], "u_factor": candidate["u_factor"], "shgc": candidate["shgc"],
                  "thickness_mm": float(construction.thickness) * 1000.0, "layers": layers if not unsupported else [],
                   "sources": candidate["sources"], "mapping": mode, "effective_only_materials": unsupported,
                  "native_layer_representation": "source_layers" if mode == "source_material_layers_and_u_factor" else "sdk_equivalent_thermal_properties",
                  "boundaries": sorted(candidate["boundaries"])}
        if isinstance(construction, OpaqueConstruction) and not unsupported:
            record["r_value"] = float(construction.r_value)
            if record["category"] in {"内门", "外门"}:
                record["mapping"] = "source_material_library_and_native_door_equivalent_u_factor"
                record["native_layer_representation"] = "equivalent_door_u_factor"
        if candidate["shgc"] is not None:
            record["visible_transmittance"] = float(construction.visible_transmittance)
        constructions.append(record)
        assignments.update((source, index) for source in candidate["sources"])
    role_assignments = {}
    for record in tuple(constructions):
        labels = []
        if record["category"] == "楼板":
            labels.extend(["非控温房间楼板", "控温与非控温空间楼板"])
            if "Ground" in record["boundaries"]:
                labels.extend(["周边地面", "非周边地面"])
            if "Outdoors" in record["boundaries"]:
                labels.extend(["挑空楼板", "架空楼板"])
        elif record["category"] == "屋顶" and "Ground" in record["boundaries"]:
            labels.append("地下室覆土顶板")
        for label in labels:
            identity = 100001 + len(constructions)
            constructions.append(dict(record, id=identity, category=label, source_construction_id=record["id"]))
            role_assignments.setdefault(label, {}).update((source, identity) for source in record["sources"])
        for label, identifiers in (native_roles or {}).items():
            sources = sorted(set(record["sources"]).intersection(identifiers).difference(role_assignments.get(label, {})))
            if not sources:
                continue
            identity = record["id"]
            if label != record["category"]:
                identity = 100001 + len(constructions)
                constructions.append(dict(record, id=identity, category=label, sources=sources,
                                          source_construction_id=record["id"], native_role="source_geometry_carrier"))
            role_assignments.setdefault(label, {}).update((source, identity) for source in sources)
    name_counts = {}
    for record in constructions:
        key = (record["category"], record["name"])
        name_counts[key] = name_counts.get(key, 0) + 1
    for record in constructions:
        if name_counts[(record["category"], record["name"])] > 1:
            record["name"] = f"{record['name']} [U={record['u_factor']:.4f};{record['id']}]"
    return NativeConstructionPlan(tuple(materials), tuple(constructions), assignments, tuple(excluded), role_assignments)


def material_node(record):
    return node("", [("Name", 2, record["name"]), ("Type", 0, 0), ("Id", 2, str(record["id"])), ("Hatch", 2, ""), ("Color", 0, 0),
                      ("Density", 1, record["density"]), ("Cond", 1, record["conductivity"]),
                      ("SpeHeat", 1, record["specific_heat"]), ("RefCoef", 1, 0.0), ("ExtCoef", 1, 0.0),
                      ("HeatStore", 1, record["heat_storage_coefficient"]),
                     ("Comment", 2, record["identifier"])],
                [node("DE", [*([("MatType", 0, record["native_material_type"])] if "native_material_type" in record else []),
                              ("HeRVal", 1, record.get("r_value", 0.0)), ("ExtHeRVal", 1, 0.0), ("Thick", 1, record["thickness_mm"]),
                             ("RouVal", 1, record["solar_absorptance"])])])


def construction_node(record):
    layers = [node("", [("A", 1, 1.0), ("Id", 2, str(layer["material_id"])), ("T", 1, layer["thickness_mm"])]) for layer in record["layers"]]
    data = [("ID", 0, record["id"]), ("AutoCal", 0, 0), ("ExRDesc", 2, ""), ("ExRVal", 1, 0.0)]
    return node("", [("Name", 2, record["name"]), ("Type", 0, 1), ("Id", 2, str(record["id"])),
                     ("Comment", 2, record["identifier"]), ("K", 1, record["u_factor"]), ("D", 1, 0.0),
                     ("SC", 1, record["shgc"] / 0.87 if record["shgc"] is not None else 0.0), ("FP", 2, "")],
                [collection("mat1", layers), node("DataEx", data)])


def construction_libraries(plan):
    categories = {}
    for record in plan.constructions:
        categories.setdefault(record["category"], []).append(construction_node(record))
    glazing = [node("", [("ID", 0, record["id"]), ("DataMode", 0, 0), ("WinSHGC", 1, record["shgc"]),
                          ("GlsSHGC", 1, record["shgc"]), ("ShgcLkSc", 0, 0), ("WinSc", 1, record["shgc"] / 0.87),
                          ("Trans", 1, record["visible_transmittance"]), ("WimK", 1, record["u_factor"])])
               for record in plan.constructions if record["shgc"] is not None]
    return [group("mats", "", [material_node(record) for record in plan.materials]),
            group("structs", "", [group("", category, items) for category, items in categories.items()]),
            collection("WinStructTrans", glazing)]


def room_type_node(name, sections, program_identifier=""):
    energy = sections["能耗分析"]
    numeric = {"People": "人员密度", "Light": "照明得热", "Equip": "设备得热", "FreshAirFlow": "新风量",
               "WinterT": "冬季温度", "SummerT": "夏季温度", "WinterFa": "冬季湿度", "SummerFa": "夏季湿度",
               "dPerSensHG": "人员显热", "dPerLatHG": "人员潜热"}
    schedules = {"sRestDay": "休息日", "sACSch": "空调作息", "sFanSch": "新风作息", "sPersonSch": "人员作息",
                 "sLightSch": "照明作息", "sEquipSch": "设备作息", "sWorkHighTSch": "工作最高温度",
                 "sWorkLowTSch": "工作最低温度", "sRestHighTSch": "休息最高温度", "sRestLowTSch": "休息最低温度"}
    conditioned = int(energy["是否空调"] == "是")
    data = [("Name2", 2, name), ("BldgType", 2, ""), ("PersonUnit", 0, 1), ("LightUnit", 0, 2),
            ("EquipUnit", 0, 2), ("FAFUnit", 0, 1), ("Heating", 0, conditioned), ("Cooling", 0, conditioned),
            *[(native, 1, float(energy[source])) for native, source in numeric.items()],
            *[(native, 2, energy[source]) for native, source in schedules.items()]]
    return node("", [("IsCustom", 0, 1), ("IsCopyFixed", 0, 0), ("Name", 2, name), ("BldType2", 2, ""),
                     ("CopySourceName", 2, ""), ("IsMainSpace", 0, 0), ("Comment", 2, program_identifier)], [node("Data", data)])


def plan_room_types(model):
    plan = assign_room_types(model, canonical_library(), by_program=True)
    records = []
    assignments = {}
    items = []
    for identifier, name in hb.room_names(model).items():
        assignment = plan.assignments[identifier]
        assignments[identifier] = name
        mapping = {}
        sections = program_to_sections(assignment.program_type, name, SpOptions(building_type=""),
                                               floor_area_m2=assignment.floor_area_m2, volume_m3=assignment.volume_m3, report=mapping)
        items.append(room_type_node(name, sections, assignment.program_identifier))
        record = {"name": name, "program_identifier": assignment.program_identifier, "program_key": program_key(assignment), "rooms": [identifier],
                  "source": "source_sdk_program_type_with_room_load_overrides" if assignment.program_overrides else "source_sdk_program_type",
                  "room_load_overrides": list(assignment.program_overrides), "sections": sections, "mapping": mapping}
        records.append(record)
    library = node("RmTypes", children=[collection("RmTypes", items), collection("RTRef", []), collection("RTSch", [])])
    return library, records, assignments


@dataclass(frozen=True)
class RoomRule:
    category: str
    candidates: tuple[str, ...]
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class RoomTypeLibrary:
    root: Path | None
    names: tuple[str, ...]
    building_type: str
    standard_name: str
    source: Path | None

    def resolve(self, candidates: tuple[str, ...], default_room_type: str | None = None) -> str:
        for candidate in candidates:
            if candidate in self.names:
                return candidate
        for candidate in candidates:
            for name in self.names:
                if normalize(candidate) and normalize(candidate) in normalize(name):
                    return name
        if default_room_type and default_room_type in self.names:
            return default_room_type
        for fallback in ("默认房间", "空房间", "办公-其它", "办公-其他"):
            if fallback in self.names:
                return fallback
        if self.names:
            return self.names[0]
        return default_room_type or (candidates[0] if candidates else "默认房间")


@dataclass(frozen=True)
class RoomTypeAssignment:
    room_identifier: str
    room_name: str
    story: str
    program_identifier: str
    room_type: str
    category: str
    source: str
    program_type: ProgramType | None = field(default=None, repr=False, compare=False)
    floor_area_m2: float | None = None
    volume_m3: float | None = None
    program_overrides: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoomTypePlan:
    assignments: dict[str, RoomTypeAssignment]
    by_type: dict[str, tuple[str, ...]]
    conflicts: dict[str, tuple[str, ...]]
    category_conflicts: dict[str, tuple[str, ...]]

RULES = (
    RoomRule(
        "kitchen_dining",
        ("餐厅", "餐厨", "四级餐厅", "办公-餐厅", "默认房间", "宾馆-3星级餐厅"),
        ("kitchen and dining", "kitchen dining", "餐厨", "厨房餐厅"),
    ),
    RoomRule(
        "office",
        ("办公-普通办公室", "办公-办公室", "办公-其它", "办公-其他", "默认房间"),
        ("office", "workroom", "workspace", "study", "办公"),
    ),
    RoomRule(
        "conference",
        ("办公-会议室", "会议室", "默认房间"),
        ("conference", "meeting", "boardroom", "会议"),
    ),
    RoomRule(
        "corridor",
        ("办公-走廊", "走廊", "过道", "默认房间"),
        ("corridor", "hallway", "hall", "passage", "走廊", "过道"),
    ),
    RoomRule(
        "restroom",
        ("办公楼卫生间", "办公-卫生间", "卫生间", "洗手间", "默认房间"),
        ("restroom", "toilet", "bathroom", "bath", "wc", "卫生间", "洗手间"),
    ),
    RoomRule(
        "classroom",
        ("学校-教室", "教室", "默认房间"),
        ("classroom", "lecture hall", "教室"),
    ),
    RoomRule(
        "patient",
        ("医院-病房", "医院-门诊", "病房", "默认房间"),
        ("patient", "ward", "病房", "门诊"),
    ),
    RoomRule(
        "retail",
        ("商场-一般商店", "商场-一般商场", "商场-高档商店", "商场-高档商场", "默认房间"),
        ("retail", "shop", "store", "sales area", "商店", "商场", "零售"),
    ),
    RoomRule(
        "hotel",
        ("宾馆-3星级客房", "宾馆-4星级客房", "宾馆-5星级客房", "宾馆-客房", "默认房间"),
        ("guest room", "guestroom", "hotel room", "客房"),
    ),
    RoomRule(
        "bedroom",
        ("卧室", "宾馆-3星级客房", "默认房间"),
        ("bedroom", "卧室"),
    ),
    RoomRule(
        "living",
        ("起居室", "默认房间"),
        ("living", "lounge", "起居"),
    ),
    RoomRule(
        "kitchen",
        ("厨房", "夏热冬冷厨房", "默认房间"),
        ("kitchen", "厨房"),
    ),
    RoomRule(
        "dining",
        ("餐厅", "食堂", "默认房间", "宾馆-3星级餐厅", "四级餐厅"),
        ("dining", "restaurant", "cafeteria", "餐厅", "食堂"),
    ),
    RoomRule(
        "storage",
        ("储物间", "默认房间"),
        ("storage", "storeroom", "warehouse", "archive", "储藏", "储物", "仓库"),
    ),
    RoomRule(
        "lobby",
        ("门厅", "宾馆-4～5星级大堂", "默认房间"),
        ("lobby", "reception", "entrance", "大堂", "门厅", "接待"),
    ),
    RoomRule(
        "stair",
        ("楼梯间", "默认房间"),
        ("stair", "stairwell", "楼梯"),
    ),
    RoomRule(
        "elevator",
        ("默认房间",),
        ("elevator", "lift", "电梯"),
    ),
    RoomRule(
        "mechanical",
        ("默认房间",),
        ("mech", "mechanical", "elec", "electrical", "equipment", "机房", "设备"),
    ),
    RoomRule(
        "laundry",
        ("默认房间",),
        ("laundry", "洗衣"),
    ),
    RoomRule(
        "plenum",
        ("空房间", "默认房间"),
        ("plenum", "attic", "空房间"),
    ),
    RoomRule(
        "default",
        ("默认房间", "空房间"),
        (),
    ),
)

DISPLAY_PRIORITY = {"plenum", "mechanical", "default"}
GENERIC_PROGRAMS = {"plenum", "generic office program"}

CATEGORY_LABELS = {
    "office": "办公",
    "conference": "会议",
    "corridor": "走廊",
    "restroom": "卫生间",
    "classroom": "教室",
    "patient": "病房",
    "retail": "商业",
    "hotel": "客房",
    "bedroom": "卧室",
    "living": "起居",
    "kitchen": "厨房",
    "kitchen_dining": "餐厨",
    "dining": "餐厅",
    "storage": "储藏",
    "lobby": "门厅",
    "stair": "楼梯",
    "elevator": "电梯",
    "mechanical": "机房",
    "laundry": "洗衣",
    "plenum": "空房间",
    "default": "其他",
}


def normalize(text: str) -> str:
    value = text.lower().replace("&", " and ")
    for char in "_-/.,:;()[]{}":
        value = value.replace(char, " ")
    return " ".join(value.split())


def canonical_library() -> RoomTypeLibrary:
    names = tuple(dict.fromkeys(rule.candidates[0] for rule in RULES))
    return RoomTypeLibrary(
        root=None,
        names=names,
        building_type="",
        standard_name="canonical",
        source=None,
    )


def match_room_type(
    library: RoomTypeLibrary,
    program_identifier: str,
    display_name: str,
    identifier: str = "",
    default_room_type: str | None = None,
) -> tuple[str, str, str]:
    display_text = " ".join((display_name, identifier))
    exact = _exact_name(library, display_text)
    if exact:
        return exact, "display", "exact"
    program_text = " ".join((program_identifier, program_identifier.split("::")[-1]))
    program_rule = _match_text(program_text)
    display_rule = _match_text(display_text)
    generic = program_identifier.lower() in GENERIC_PROGRAMS or "::" not in program_identifier
    if display_rule and (
        program_rule is None
        or generic
        or program_rule.category in DISPLAY_PRIORITY
    ):
        rule = display_rule
        source = "display"
    elif program_rule is not None:
        rule = program_rule
        source = "program"
    elif display_rule is not None:
        rule = display_rule
        source = "display"
    else:
        rule = RULES[-1]
        source = "default"
    room_type = library.resolve(rule.candidates, default_room_type)
    return room_type, source, rule.category


def _exact_name(library: RoomTypeLibrary, text: str) -> str | None:
    normalized = normalize(text)
    for name in library.names:
        candidate = normalize(name)
        if candidate and candidate in normalized:
            return name
    return None


def _match_text(text: str) -> RoomRule | None:
    normalized = normalize(text)
    best: tuple[int, RoomRule] | None = None
    for rule in RULES:
        for keyword in rule.keywords:
            candidate = normalize(keyword)
            if candidate and candidate in normalized:
                if best is None or len(candidate) > best[0]:
                    best = (len(candidate), rule)
    return best[1] if best else None


def assign_room_types(
    model,
    library: RoomTypeLibrary,
    default_room_type: str | None = None,
    *,
    by_program: bool = False,
) -> RoomTypePlan:
    assignments: dict[str, RoomTypeAssignment] = {}
    scale = conversion_factor_to_meters(model.units)
    for room in model.rooms:
        energy = room.properties.energy
        program_type = energy.program_type
        load_fields = ("people", "lighting", "electric_equipment", "gas_equipment", "service_hot_water", "infiltration", "ventilation", "exhaust", "setpoint")
        overrides = tuple(name for name in load_fields if getattr(energy, name) != getattr(program_type, name))
        if overrides:
            program_type = program_type.duplicate()
            for name in overrides:
                setattr(program_type, name, getattr(energy, name))
        program_identifier = program_type.identifier
        room_type, source, category = match_room_type(
            library,
            program_identifier,
            room.display_name or room.identifier,
            room.identifier,
            default_room_type,
        )
        assignments[room.identifier] = RoomTypeAssignment(
            room_identifier=room.identifier,
            room_name=room.display_name or room.identifier,
            story=room.story or "Unassigned",
            program_identifier=program_identifier,
            room_type=room_type,
            category=category,
            source=source,
            program_type=program_type,
            floor_area_m2=float(room.floor_area) * scale ** 2,
            volume_m3=float(room.volume) * scale ** 3,
            program_overrides=overrides,
        )
    plan = _build_plan(assignments)
    return split_room_types(plan, library, by_program=True) if by_program else plan


def program_key(assignment: RoomTypeAssignment) -> str:
    program = assignment.program_type
    data: dict[str, object] = {
        "program": program.to_dict() if program is not None else assignment.program_identifier
    }
    ventilation = program.ventilation if program is not None else None
    if ventilation is not None:
        area = assignment.floor_area_m2
        if ventilation.flow_per_zone:
            data["floor_area_m2"] = round(area, 8) if area is not None else None
        if ventilation.air_changes_per_hour:
            volume = assignment.volume_m3
            data["volume_per_area_m"] = (
                round(volume / area, 8) if volume is not None and area else None
            )
    payload = json.dumps(data, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _build_plan(assignments: dict[str, RoomTypeAssignment]) -> RoomTypePlan:
    by_type: dict[str, list[str]] = {}
    programs: dict[str, dict[str, str]] = {}
    categories: dict[str, set[str]] = {}
    for room_id, assignment in assignments.items():
        name = assignment.room_type
        by_type.setdefault(name, []).append(room_id)
        programs.setdefault(name, {})[program_key(assignment)] = assignment.program_identifier
        categories.setdefault(name, set()).add(assignment.category)
    conflicts = {}
    for name, values in programs.items():
        if len(values) > 1:
            labels = tuple(sorted(values.values()))
            if len(set(labels)) < len(labels):
                labels = tuple(sorted(f"{identifier} [{key[:8]}]" for key, identifier in values.items()))
            conflicts[name] = labels
    return RoomTypePlan(
        assignments=assignments,
        by_type={name: tuple(values) for name, values in by_type.items()},
        conflicts=conflicts,
        category_conflicts={
            name: tuple(sorted(values))
            for name, values in categories.items()
            if len(values) > 1
        },
    )


def split_room_types(
    plan: RoomTypePlan,
    library: RoomTypeLibrary,
    *,
    by_program: bool = False,
) -> RoomTypePlan:
    groups: dict[tuple[str, str, str], list[str]] = {}
    for room_id, assignment in plan.assignments.items():
        key = program_key(assignment) if by_program else ""
        groups.setdefault((assignment.room_type, assignment.category, key), []).append(room_id)
    base_groups: dict[str, int] = {}
    for base, _, _ in groups:
        base_groups[base] = base_groups.get(base, 0) + 1
    used = set(library.names) | set(plan.by_type)
    assignments: dict[str, RoomTypeAssignment] = {}
    for (base, category, key), room_ids in groups.items():
        if base_groups[base] == 1:
            name = base
        else:
            suffix = CATEGORY_LABELS.get(category, category)
            if by_program:
                identifier = plan.assignments[room_ids[0]].program_identifier
                label = normalize(identifier.split("::")[-1]).replace(" ", "-")
                suffix = f"{suffix}-{label}-{key[:8]}"
            name = f"{base}-{suffix}"
            if name in used:
                index = 2
                while f"{base}-{suffix}-{index}" in used:
                    index += 1
                name = f"{base}-{suffix}-{index}"
        used.add(name)
        for room_id in room_ids:
            assignments[room_id] = replace(plan.assignments[room_id], room_type=name)
    return _build_plan(assignments)

CATEGORY_PROGRAMS = {
    "office": "2019::MediumOffice::OpenOffice",
    "conference": "2019::MediumOffice::Conference",
    "corridor": "2019::MediumOffice::Corridor",
    "restroom": "2019::MediumOffice::Restroom",
    "classroom": "2019::PrimarySchool::Classroom",
    "patient": "2019::Hospital::PatRoom",
    "retail": "2019::Retail::Retail",
    "hotel": "2019::LargeHotel::GuestRoom",
    "bedroom": "2019::HighriseApartment::Apartment",
    "living": "2019::HighriseApartment::Apartment",
    "kitchen": "2019::FullServiceRestaurant::Kitchen",
    "kitchen_dining": "2019::FullServiceRestaurant::Dining",
    "dining": "2019::FullServiceRestaurant::Dining",
    "storage": "2019::MediumOffice::Storage",
    "lobby": "2019::LargeHotel::Lobby",
    "stair": "2019::MediumOffice::Stair",
    "mechanical": "2019::MediumOffice::Elec/MechRoom",
    "laundry": "2019::MediumOffice::Storage",
    "elevator": "2019::MediumOffice::Storage",
    "plenum": "Plenum",
    "default": "2019::MediumOffice::OpenOffice",
}


@dataclass(frozen=True)
class SpOptions:
    building_type: str = "办公建筑"
    humidity_heating: float = 40.0
    humidity_cooling: float = 60.0
    rest_days: str = "WEEK6, WEEK7"
    latent_fraction: float | None = None


def value_text(value: float) -> str:
    text = f"{float(value):.3f}".rstrip("0").rstrip(".")
    return text or "0"


def compress_schedule(values: Sequence[float]) -> str:
    groups: list[tuple[float, int]] = []
    for value in values:
        rounded = round(float(value), 3)
        if groups and abs(groups[-1][0] - rounded) < 1e-9:
            groups[-1] = (rounded, groups[-1][1] + 1)
        else:
            groups.append((rounded, 1))
    parts = []
    for value, count in groups:
        text = value_text(value)
        parts.append(f"{count}*{text}" if count > 1 else text)
    return ", ".join(parts)


def day_values(schedule, fallback: float = 0.0, *, report: dict | None = None) -> list[float]:
    details = {
        "schedule_identifier": getattr(schedule, "identifier", None),
        "timestep_per_hour": 1,
        "annual_expansion": "deferred",
    }
    if schedule is None:
        details.update(source="fallback", fallback_value=float(fallback))
        if report is not None:
            report.update(details)
        return [float(fallback)] * 24
    days = list(getattr(schedule, "typical_day_schedules", ()))
    if not days:
        start = getattr(schedule, "start_date", None)
        values = schedule.values_at_timestep(1, start_date=start, end_date=start)
        details.update(source="fixed_interval_first_day", selected_day=str(start))
    else:
        preferred = [
            day for day in days
            if "wkdy" in day.identifier.lower()
            or "weekday" in day.identifier.lower()
        ]
        day = preferred[0] if preferred else days[0]
        values = day.values_at_timestep(1)
        details.update(
            source="ruleset_typical_day",
            selected_day=day.identifier,
            available_days=[item.identifier for item in days],
        )
    values = [float(value) for value in values]
    if len(values) < 24:
        values.extend([values[-1] if values else float(fallback)] * (24 - len(values)))
        details["padding"] = "last_value_or_fallback"
    if report is not None:
        report.update(details)
    return values[:24]


def binary_schedule(values: Sequence[float]) -> list[float]:
    return [1.0 if value > 0.01 else 0.0 for value in values]


def people_heat(program, options: SpOptions) -> tuple[float, float]:
    people = program.people
    if people is None:
        return 0.0, 0.0
    sensible = float(people.activity_max_sensible)
    latent = float(people.activity_max_latent)
    if options.latent_fraction is not None and not isinstance(people.latent_fraction, (int, float)):
        fraction = min(max(float(options.latent_fraction), 0.0), 1.0)
        activity = sensible + latent
        return activity * (1.0 - fraction), activity * fraction
    return sensible, latent


def ventilation_per_person(
    program,
    floor_area_m2: float | None = None,
    volume_m3: float | None = None,
    *,
    report: dict | None = None,
) -> float:
    ventilation = program.ventilation
    if ventilation is None:
        if report is not None:
            report.update(source="absent", status="mapped", value_m3_h_person=0.0)
        return 0.0
    people = program.people
    people_per_area = float(people.people_per_area) if people is not None else 0.0
    if report is not None:
        report.update(
            source="Ventilation.room_absolute_flow",
            status="pending",
            method=ventilation.method,
            floor_area_m2=floor_area_m2,
            volume_m3=volume_m3,
        )
    if ventilation.flow_per_zone and (floor_area_m2 is None or floor_area_m2 <= 0):
        if report is not None:
            report["status"] = "requires_room_geometry"
        raise ValueError("Zone ventilation requires a positive floor_area_m2")
    if ventilation.air_changes_per_hour and (
        floor_area_m2 is None or floor_area_m2 <= 0 or volume_m3 is None or volume_m3 <= 0
    ):
        if report is not None:
            report["status"] = "requires_room_geometry"
        raise ValueError("Air-change ventilation requires positive floor_area_m2 and volume_m3")
    area = floor_area_m2 if floor_area_m2 is not None and floor_area_m2 > 0 else 1.0
    room = SimpleNamespace(
        floor_area=area,
        volume=volume_m3 or 0.0,
        properties=SimpleNamespace(energy=SimpleNamespace(people=people)),
    )
    flow = float(ventilation.room_absolute_flow(room))
    person_count = people_per_area * area
    if flow > 0 and person_count <= 0:
        if report is not None:
            report.update(status="requires_positive_occupancy", total_flow_m3_s=flow)
        raise ValueError("SP per-person ventilation requires positive source people density")
    value = flow * 3600.0 / person_count if person_count > 0 else 0.0
    if report is not None:
        report.update(
            status="mapped",
            calculation_area_m2=area,
            design_people=person_count,
            total_flow_m3_s=flow,
            value_m3_h_person=value,
            effectiveness=min(ventilation.effectiveness_cooling, ventilation.effectiveness_heating),
            secondary_recirculation=ventilation.secondary_recirculation,
        )
    return value


def program_to_sections(
    program,
    name: str,
    options: SpOptions,
    *,
    floor_area_m2: float | None = None,
    volume_m3: float | None = None,
    report: dict | None = None,
) -> dict[str, dict[str, str]]:
    people = program.people
    lighting = program.lighting
    equipment = program.electric_equipment
    setpoint = program.setpoint
    ventilation = program.ventilation

    area_per_person = float(people.area_per_person) if people is not None else 0.0
    lighting_watts = float(lighting.watts_per_area) if lighting is not None else 0.0
    equipment_watts = float(equipment.watts_per_area) if equipment is not None else 0.0
    heating = float(setpoint.heating_setpoint) if setpoint and setpoint.heating_setpoint is not None else 20.0
    cooling = float(setpoint.cooling_setpoint) if setpoint and setpoint.cooling_setpoint is not None else 26.0
    heating_humidity = (
        float(setpoint.humidifying_setpoint)
        if setpoint and setpoint.humidifying_setpoint is not None
        else options.humidity_heating
    )
    cooling_humidity = (
        float(setpoint.dehumidifying_setpoint)
        if setpoint and setpoint.dehumidifying_setpoint is not None
        else options.humidity_cooling
    )
    rest_heating = (
        float(setpoint.heating_setback)
        if setpoint and setpoint.heating_setback is not None
        else heating
    )
    rest_cooling = (
        float(setpoint.cooling_setback)
        if setpoint and setpoint.cooling_setback is not None
        else cooling
    )

    schedule_reports: dict[str, dict] = {}

    def sample(label, schedule, fallback):
        details: dict = {}
        values = day_values(schedule, fallback, report=details)
        schedule_reports[label] = details
        return values

    occupancy = sample("people", people.occupancy_schedule if people is not None else None, 0.0)
    light = sample("lighting", lighting.schedule if lighting is not None else None, 0.0)
    equip = sample("electric_equipment", equipment.schedule if equipment is not None else None, 0.0)
    hvac_source = occupancy if any(value > 0.01 for value in occupancy) else light
    hvac = binary_schedule(hvac_source) if setpoint is not None else [0.0] * 24
    vent_schedule = ventilation.schedule if ventilation is not None else None
    vent = sample("ventilation", vent_schedule, 1.0 if ventilation is not None else 0.0)
    heating_values = sample("heating", setpoint.heating_schedule if setpoint else None, heating)
    cooling_values = sample("cooling", setpoint.cooling_schedule if setpoint else None, cooling)
    sensible, latent = people_heat(program, options)
    ventilation_report: dict = {}
    if report is not None:
        automatic_latent = people is not None and not isinstance(people.latent_fraction, (int, float))
        report.update(
            program_identifier=program.identifier,
            scope="typical_day",
            annual_expansion="deferred",
            deferred_schedule_features=["calendar", "seasonal_rules", "weekends", "holidays", "design_days"],
            schedules=schedule_reports,
            ventilation=ventilation_report,
            units={
                "人员密度": "m2/person",
                "照明得热": "W/m2",
                "设备得热": "W/m2",
                "人员显热": "W/person",
                "人员潜热": "W/person",
                "新风量": "m3/h/person",
                "temperature": "C",
                "humidity": "%",
            },
            assumptions={
                "hvac_schedule": "binary_occupancy_or_lighting" if setpoint else "unconditioned",
                "people_heat": (
                    "sdk_activity_peak_and_option_latent_fraction"
                    if automatic_latent and options.latent_fraction is not None
                    else "sdk_activity_max_sensible_and_latent"
                ),
                "autocalculated_latent_fraction": (
                    options.latent_fraction if options.latent_fraction is not None else 0.5
                ) if automatic_latent else None,
                "rest_days": options.rest_days,
                "temperature": "source_setpoint" if setpoint else "unconditioned_placeholder",
                "heating_humidity": "source" if setpoint and setpoint.humidifying_schedule else "option",
                "cooling_humidity": "source" if setpoint and setpoint.dehumidifying_schedule else "option",
            },
            deferred_loads=[
                key for key in ("gas_equipment", "service_hot_water", "infiltration", "exhaust")
                if getattr(program, key, None) is not None
            ],
        )
    fresh_air = ventilation_per_person(
        program, floor_area_m2, volume_m3, report=ventilation_report
    )

    energy = {
        "是否空调": "是" if setpoint is not None else "否",
        "冬季温度": value_text(heating),
        "夏季温度": value_text(cooling),
        "冬季湿度": value_text(heating_humidity),
        "夏季湿度": value_text(cooling_humidity),
        "新风量": value_text(fresh_air),
        "人员密度": value_text(area_per_person),
        "照明得热": value_text(lighting_watts),
        "设备得热": value_text(equipment_watts),
        "人员显热": value_text(sensible),
        "人员潜热": value_text(latent),
        "休息日": options.rest_days,
        "空调作息": compress_schedule(hvac),
        "新风作息": compress_schedule(vent),
        "人员作息": compress_schedule(occupancy),
        "照明作息": compress_schedule(light),
        "设备作息": compress_schedule(equip),
        "工作最高温度": compress_schedule(cooling_values),
        "工作最低温度": compress_schedule(heating_values),
        "休息最高温度": compress_schedule([rest_cooling] * 24),
        "休息最低温度": compress_schedule([rest_heating] * 24),
    }
    design = {
        "冬季温度": value_text(heating),
        "夏季温度": value_text(cooling),
        "冬季湿度": value_text(heating_humidity),
        "夏季湿度": value_text(cooling_humidity),
        "新风量": value_text(fresh_air),
        "人员密度": value_text(area_per_person),
        "照明得热": value_text(lighting_watts),
        "设备得热": value_text(equipment_watts),
        "群集系数": "1.0",
        "劳动强度": "1",
        "新风作息": compress_schedule(vent),
        "人员作息": compress_schedule(occupancy),
        "照明作息": compress_schedule(light),
        "设备作息": compress_schedule(equip),
    }
    return {
        "基本概况": {"建筑类型": options.building_type, "房间类型": name},
        "能耗分析": energy,
        "设计负荷": design,
    }
