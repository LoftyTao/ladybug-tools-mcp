"""Direct binary DWG container writer and reader."""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field


class BitWriter:
    def __init__(self):
        self.data = bytearray()
        self.position = 0

    def bits(self, value, count):
        if count < 0 or value < 0 or value >= 1 << count:
            raise ValueError("Bit values require their declared unsigned range")
        for shift in range(count - 1, -1, -1):
            index, bit = divmod(self.position, 8)
            if index == len(self.data):
                self.data.append(0)
            mask = 0x80 >> bit
            if value >> shift & 1:
                self.data[index] |= mask
            else:
                self.data[index] &= 255 ^ mask
            self.position += 1

    def raw(self, data):
        for value in data:
            self.bits(value, 8)

    def b(self, value):
        self.bits(int(value), 1)

    def bb(self, value):
        self.bits(value, 2)

    def rc(self, value):
        self.bits(value, 8)

    def rs(self, value):
        self.raw(struct.pack("<H", value))

    def rl(self, value):
        self.raw(struct.pack("<I", value))

    def rd(self, value):
        if not math.isfinite(value):
            raise ValueError("Drawing coordinates require finite values")
        self.raw(struct.pack("<d", value))

    def bs(self, value):
        if not 0 <= value <= 65535:
            raise ValueError("BS values require the unsigned sixteen-bit range")
        if value == 0:
            self.bb(2)
        elif value == 256:
            self.bb(3)
        elif value < 256:
            self.bb(1)
            self.rc(value)
        else:
            self.bb(0)
            self.rs(value)

    def bl(self, value):
        if not 0 <= value <= 0xFFFFFFFF:
            raise ValueError("BL values require the unsigned thirty-two-bit range")
        if value == 0:
            self.bb(2)
        elif value < 256:
            self.bb(1)
            self.rc(value)
        else:
            self.bb(0)
            self.rl(value)

    def bd(self, value):
        if value == 0.0:
            self.bb(2)
        elif value == 1.0:
            self.bb(1)
        else:
            self.bb(0)
            self.rd(value)

    def point(self, values):
        for value in values:
            self.bd(float(value))

    def dd(self, default, value):
        self.bb(0 if value == default else 3)
        if value != default:
            self.rd(value)

    def text(self, value):
        if "\0" in value:
            raise ValueError("Drawing strings require printable text")
        data = value.encode("gbk", errors="strict")
        self.bs(len(data))
        self.raw(data)

    def handle(self, code, value):
        if not 0 <= code < 16 or not 0 <= value < 1 << 64:
            raise ValueError("Handle values require the declared DWG range")
        size = (value.bit_length() + 7) // 8
        self.rc(code << 4 | size)
        self.raw(value.to_bytes(size, "big"))

    def append(self, other):
        for index in range(other.position):
            self.b(other.data[index // 8] >> (7 - index % 8) & 1)

    def patch_rl(self, position, value):
        end = self.position
        self.position = position
        self.rl(value)
        self.position = end

    def finish(self):
        return bytes(self.data)


class BitReader:
    def __init__(self, data, position=0, limit=None):
        self.data = memoryview(data)
        self.position = position
        self.limit = len(data) * 8 if limit is None else limit
        if not 0 <= position <= self.limit <= len(data) * 8:
            raise ValueError("Bit readers require bounded positions")

    def bits(self, count):
        if count < 0 or self.position + count > self.limit:
            raise ValueError("Drawing data requires a complete bounded field")
        first, offset = divmod(self.position, 8)
        size = (offset + count + 7) // 8
        value = int.from_bytes(self.data[first:first + size], "big")
        self.position += count
        return (value >> (size * 8 - offset - count)) & ((1 << count) - 1)

    def raw(self, count):
        if count < 0 or self.position + count * 8 > self.limit:
            raise ValueError("Drawing data requires a complete bounded byte field")
        if self.position % 8 == 0:
            first = self.position // 8
            self.position += count * 8
            return bytes(self.data[first:first + count])
        return self.bits(count * 8).to_bytes(count, "big")

    def b(self):
        return self.bits(1)

    def bb(self):
        return self.bits(2)

    def rc(self):
        return self.bits(8)

    def rs(self):
        return struct.unpack("<H", self.raw(2))[0]

    def rl(self):
        return struct.unpack("<I", self.raw(4))[0]

    def rd(self):
        value = struct.unpack("<d", self.raw(8))[0]
        if not math.isfinite(value):
            raise ValueError("Drawing data requires finite doubles")
        return value

    def bs(self):
        code = self.bb()
        return self.rs() if code == 0 else self.rc() if code == 1 else 0 if code == 2 else 256

    def bl(self):
        code = self.bb()
        if code == 3:
            raise ValueError("BL data requires a defined compression tag")
        return self.rl() if code == 0 else self.rc() if code == 1 else 0

    def bd(self):
        code = self.bb()
        if code == 3:
            raise ValueError("BD data requires a defined compression tag")
        return self.rd() if code == 0 else 1.0 if code == 1 else 0.0

    def point(self, count=3):
        return tuple(self.bd() for _ in range(count))

    def dd(self, default):
        code = self.bb()
        if code not in (0, 3):
            raise ValueError("Native default doubles require complete values or the declared default")
        return default if code == 0 else self.rd()

    def text(self):
        return self.raw(self.bs()).decode("gbk", errors="strict")

    def handle(self):
        tag = self.rc()
        size = tag & 15
        if size > 8:
            raise ValueError("Handle payloads require at most eight bytes")
        return tag >> 4, int.from_bytes(self.raw(size), "big")


def _crc_table():
    values = []
    for value in range(256):
        for _ in range(8):
            value = value >> 1 ^ (0xA001 if value & 1 else 0)
        values.append(value)
    return tuple(values)


_CRC_TABLE = _crc_table()


def crc16(data, seed=0xC0C1):
    value = seed
    for item in data:
        value = value >> 8 ^ _CRC_TABLE[(value ^ item) & 255]
    return value


def modular_short(value):
    if not 0 <= value <= 0x3FFFFFFF:
        raise ValueError("Object sizes require the thirty-bit DWG range")
    if value < 0x8000:
        return struct.pack("<H", value)
    return struct.pack("<HH", value & 0x7FFF | 0x8000, value >> 15)


def modular_char(value):
    sign = 0x40 if value < 0 else 0
    value = abs(value)
    result = bytearray()
    for _ in range(4):
        part = value & 0x7F
        value >>= 7
        if value == 0 and part < 0x40:
            result.append(part | sign)
            return bytes(result)
        result.append(part | 0x80)
    raise ValueError("Object-map deltas require the four-byte DWG range")


def read_modular_char(data, position, limit):
    value = 0
    for shift in range(0, 28, 7):
        if position >= limit:
            raise ValueError("Object-map entries require complete modular values")
        part = data[position]
        position += 1
        if part & 0x80:
            value |= (part & 0x7F) << shift
        else:
            value |= (part & 0x3F) << shift
            return (-value if part & 0x40 else value), position
    raise ValueError("Object-map values require a terminating byte")

DIRECTORY_SENTINEL = bytes.fromhex("95a04e2899821ae55e41e05f9d3a4d00")
HEADER_SENTINEL = bytes.fromhex("cf7b1f23fdde38a95f7c68b84e6d335f")
CLASSES_SENTINEL = bytes.fromhex("8da1c4b8c4a9f8c5c0dcf45fe7cfb68a")


@dataclass(frozen=True)
class ClassDefinition:
    number: int
    cpp_name: str
    name: str
    application: str = "ObjectDBX Classes"
    entity: bool = False
    proxy_flags: int = 0


@dataclass
class Entity:
    handle: int
    type_code: int
    layer: str
    body: object
    references: list = field(default_factory=list)
    dictionary: int = 0
    color: int = 256
    owner: int = 0
    metadata: dict = field(default_factory=dict)
    xdata: tuple = ()
    application_xdata: dict = field(default_factory=dict)


class Drawing:
    def __init__(self, layers, styles=()):
        self.next_handle = 1
        self.controls = [self.allocate() for _ in range(10)]
        self.dictionaries = [self.allocate() for _ in range(6)]
        for name in ("model", "paper", "layer", "style", "bylayer", "byblock", "continuous", "model_begin", "model_end", "paper_begin", "paper_end", "normal_plotstyle", "model_layout", "paper_layout", "dimstyle"):
            setattr(self, name, self.allocate())
        self.appid = self.allocate()
        self.appids = {"HB_BESI": self.appid}
        self.layers = {"0": (self.layer, 7, True)}
        for name, color, visible in layers:
            if name in self.layers:
                raise ValueError("Layer names require unique drawing definitions")
            self.layers[name] = (self.allocate(), color, visible)
        self.styles = {"Standard": self.style}
        self.styles.update((name, self.allocate()) for name in styles)
        self.classes = [
            ClassDefinition(500, "AcDbDictionaryWithDefault", "ACDBDICTIONARYWDFLT"),
            ClassDefinition(501, "AcDbPlaceHolder", "ACDBPLACEHOLDER"),
            ClassDefinition(502, "AcDbLayout", "LAYOUT"),
        ]
        self.entities = []
        self.additional_objects = []
        self.dictionary_entries = {}
        self.named_objects = {}
        self.blocks = {}
        self.block_entities = {}
        self.owned_entities = {}
        self.block_metadata = {}
        self.block_xdata = {}
        self.extents = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))

    def allocate(self):
        value = self.next_handle
        self.next_handle += 1
        return value

    def add_class(self, cpp_name, name, entity=True, application='"SWR_ARCHCORE"', proxy_flags=1):
        definition = ClassDefinition(500 + len(self.classes), cpp_name, name, application, entity, proxy_flags)
        self.classes.append(definition)
        return definition.number

    def add_appid(self, name):
        if name not in self.appids:
            self.appids[name] = self.allocate()
        return self.appids[name]

    def add_entity(self, type_code, layer, body, **kwargs):
        entity = Entity(self.allocate(), type_code, layer, body, **kwargs)
        if entity.owner:
            collection = self.block_entities if entity.owner in self.block_entities else self.owned_entities
            collection.setdefault(entity.owner, []).append(entity)
        else:
            self.entities.append(entity)
        return entity

    def add_object(self, type_code, handle, owner, body, references=(), dictionary=0):
        self.additional_objects.append((handle, object_payload(type_code, handle, owner, body, references, dictionary)))

    def add_dictionary(self, owner, entries):
        handle = self.allocate()
        self.set_dictionary_entries(handle, owner, entries)
        return handle

    def set_dictionary_entries(self, handle, owner, entries):
        entries = dict(entries)
        self.dictionary_entries[handle] = (owner, entries)
        self.additional_objects = [(identity, payload) for identity, payload in self.additional_objects if identity != handle]
        def body(w):
            w.bl(len(entries))
            w.bs(1)
            w.rc(1)
            for name in entries:
                w.text(name)
        self.add_object(0x2A, handle, owner, body, [(3, value) for value in entries.values()])

    def add_xrecord(self, handle, owner, tags):
        raw = bytearray()
        for code, value in tags:
            raw += struct.pack("<H", code)
            if code == 280:
                raw += struct.pack("B", value)
            elif code in (1, 301, 302):
                text = str(value).encode("gbk") + b"\0"
                raw += struct.pack("<HB", len(text), 39) + text
            else:
                raise ValueError("Native XRECORD fields require a supported group type")
        def body(w):
            w.bl(len(raw))
            w.raw(raw)
            w.bs(1)
        self.additional_objects.append((handle, object_payload(0x4F, handle, owner, body, duplicate_owner=True)))

    def add_line(self, start, end, layer="0", color=256, owner=0):
        def body(w):
            zero = start[2] == 0 and end[2] == 0
            w.b(zero)
            for axis in range(2 if zero else 3):
                w.rd(start[axis])
                w.dd(start[axis], end[axis])
            w.b(1)
            w.b(1)
        return self.add_entity(0x13, layer, body, color=color, owner=owner)

    def add_polyline(self, vertices, layer="0", closed=True, elevation=0.0, owner=0, normal=(0.0, 0.0, 1.0)):
        vertices = tuple(vertices)
        if len(vertices) < 2:
            raise ValueError("Polylines require at least two vertices")
        def body(w):
            tilted = tuple(normal) != (0.0, 0.0, 1.0)
            w.bs((512 if closed else 0) | (8 if elevation else 0) | int(tilted))
            if elevation:
                w.bd(elevation)
            if tilted:
                w.point(normal)
            w.bl(len(vertices))
            w.rd(vertices[0][0])
            w.rd(vertices[0][1])
            for previous, current in zip(vertices, vertices[1:]):
                w.dd(previous[0], current[0])
                w.dd(previous[1], current[1])
        return self.add_entity(0x4D, layer, body, owner=owner)

    def add_text(self, text, position, height, layer="0"):
        def body(w):
            w.rc(255 if position[2] == 0 else 254)
            if position[2] != 0:
                w.rd(position[2])
            w.rd(position[0])
            w.rd(position[1])
            w.b(1)
            w.b(1)
            w.rd(height)
            w.text(text)
        return self.add_entity(1, layer, body, references=[(5, self.style)])

    def add_polyface(self, triangles, layer="0", xdata=()):
        entity = self.add_entity(0x1D, layer, None, xdata=tuple(xdata))
        try:
            self.set_polyface(entity, triangles, max_vertices=3)
        except ValueError:
            self.entities.remove(entity)
            raise
        return entity

    def set_polyface(self, entity, polygons, max_vertices=4):
        vertices = []
        indices = {}
        faces = []
        for polygon in polygons:
            if not 3 <= len(polygon) <= max_vertices:
                raise ValueError("Polyface geometry requires triangular faces or enabled quadrilaterals")
            face = []
            for point in polygon:
                point = tuple(float(value) for value in point)
                if len(point) != 3:
                    raise ValueError("Polyface vertices require three coordinates")
                if point not in indices:
                    vertices.append(point)
                    indices[point] = len(vertices)
                face.append(indices[point])
            faces.append((*face, 0) if len(face) == 3 else tuple(face))
        if not faces or len(vertices) > 32767 or len(faces) > 32767:
            raise ValueError("Polyface geometry requires bounded nonempty vertex and face lists")
        references = []
        def body(w):
            w.bs(len(vertices))
            w.bs(len(faces))
        entity.type_code, entity.body, entity.references = 0x1D, body, references
        for point in vertices:
            def vertex(w, point=point):
                w.rc(192)
                w.point(point)
            self.add_entity(0x0D, entity.layer, vertex, owner=entity.handle)
        for face in faces:
            def record(w, face=face):
                for index in face:
                    w.bs(index)
            self.add_entity(0x0E, entity.layer, record, owner=entity.handle)
        children = self.owned_entities[entity.handle]
        references.extend(((4, children[0].handle), (4, children[-1].handle)))
        end = self.add_entity(6, entity.layer, lambda w: None, owner=entity.handle)
        references.append((3, end.handle))

    def add_block(self, name):
        if name in self.blocks:
            return self.blocks[name][0]
        self.blocks[name] = tuple(self.allocate() for _ in range(3))
        self.block_entities[self.blocks[name][0]] = []
        return self.blocks[name][0]

    def bytes(self):
        entity_rows = []
        for entities in (self.entities, *self.block_entities.values(), *self.owned_entities.values()):
            for index, entity in enumerate(entities):
                previous = entities[index - 1].handle if index else 0
                following = entities[index + 1].handle if index + 1 < len(entities) else 0
                entity_rows.append((entity.handle, entity_payload(entity, self, previous, following)))
        rows = entity_rows + database_objects(self) + self.additional_objects
        return encode_container(self, rows)


def entity_payload(entity, drawing, previous=0, following=0):
    w = BitWriter()
    w.bs(entity.type_code)
    size_position = w.position
    w.rl(0)
    w.handle(0, entity.handle)
    if entity.xdata:
        data = extended_data(entity.xdata)
        w.bs(len(data))
        w.handle(5, drawing.appid)
        w.raw(data)
    for name, tags in entity.application_xdata.items():
        data = extended_data(tags)
        w.bs(len(data))
        w.handle(5, drawing.appids[name])
        w.raw(data)
    w.bs(0)
    w.b(0)
    w.bb(0)
    w.bl(0)
    w.b(0)
    w.bs(entity.color)
    w.bd(1.0)
    w.bb(0)
    w.bb(0)
    w.bs(0)
    w.rc(29)
    entity.body(w)
    w.patch_rl(size_position, w.position)
    for code, value in [(4, entity.owner or drawing.model), (3, entity.dictionary), (4, previous), (4, following), (5, drawing.layers[entity.layer][0]), *entity.references]:
        w.handle(code, value)
    return w.finish()


def object_payload(type_code, handle, owner, body, references=(), dictionary=0, duplicate_owner=False, xdata=()):
    w = BitWriter()
    w.bs(type_code)
    size_position = w.position
    w.rl(0)
    w.handle(0, handle)
    for appid, tags in xdata:
        data = extended_data(tags)
        w.bs(len(data))
        w.handle(5, appid)
        w.raw(data)
    w.bs(0)
    w.bl(0)
    body(w)
    w.patch_rl(size_position, w.position)
    if duplicate_owner:
        w.handle(4, owner)
    for code, value in [(4, owner), (3, dictionary), *references]:
        w.handle(code, value)
    return w.finish()


def extended_data(tags):
    result = bytearray()
    for code, value in tags:
        result.append(code - 1000)
        if code == 1000:
            text = value.encode("gbk") + b"\0"
            if len(text) > 255:
                raise ValueError("Extended strings require at most 255 encoded bytes")
            result += struct.pack("B", len(text)) + struct.pack(">H", 39) + text
        elif code in (1010, 1011, 1012, 1013):
            result += struct.pack("<ddd", *value)
        elif code in (1040, 1041, 1042):
            result += struct.pack("<d", value)
        elif code == 1005:
            result += struct.pack(">Q", value)
        elif code == 1071:
            result += struct.pack("<i", value)
        elif code == 1070:
            result += struct.pack("<h", value)
        else:
            raise ValueError("Extended fields require a supported native type")
    return result


def table_name(w, name):
    w.text(name)
    w.b(0)
    w.bs(0)
    w.b(0)


def dimensions(w, style=0):
    for value in (1.0, 2.5, 0.625, 3.75, 1.25, 0.0, 0.0, 0.0, 0.0):
        w.bd(value)
    for _ in range(6):
        w.b(0)
    for value in (1, 8, 0):
        w.bs(value)
    for value in (2.5, 2.5, 0.0, 0.03937007874015748, 1.0, 0.0, 1.0, 0.625, 0.0):
        w.bd(value)
    w.b(0)
    w.bs(2)
    for value in (1, 0, 0, 0):
        w.b(value)
    for _ in range(3):
        w.bs(0)
    for value in (0, 2, 2, 2, 2, 0, 0, 2, 46, 0, 0):
        w.bs(value)
    w.b(0)
    w.b(0)
    for value in (1, 0, 0, 0):
        w.bs(value)
    w.b(0)
    w.bs(3)
    if style:
        for handle in (style, 0, 0, 0, 0):
            w.handle(5, handle)
    w.bs(65534)
    w.bs(65534)


def layout_body(w, name):
    w.text("")
    w.text("")
    w.bs(1024)
    for value in (0.0, 0.0, 0.0, 0.0, 420.0, 297.0):
        w.bd(value)
    w.text("")
    w.bd(0.0)
    w.bd(0.0)
    for value in (1, 0, 0):
        w.bs(value)
    for _ in range(4):
        w.bd(0.0)
    w.text("")
    w.bd(1.0)
    w.bd(1.0)
    w.text("")
    w.bs(16)
    for value in (1.0, 0.0, 0.0):
        w.bd(value)
    w.text(name)
    w.bl(0 if name == "Model" else 1)
    w.bs(1)
    w.point((0.0, 0.0, 0.0))
    for value in (0.0, 0.0, 420.0, 297.0):
        w.rd(value)
    for point in ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)):
        w.point(point)
    w.bd(0.0)
    w.bs(0)
    w.point((0.0, 0.0, 0.0))
    w.point((0.0, 0.0, 0.0))


def database_objects(d):
    result = []
    def add(typ, handle, owner, body, references=()):
        result.append((handle, object_payload(typ, handle, owner, body, references)))
    for index, (handle, typ) in enumerate(zip(d.controls, (0x30, 0x32, 0x34, 0x38, 0x3C, 0x3E, 0x40, 0x42, 0x44, 0x46))):
        entries = list(value[0] for value in d.blocks.values()) if index == 0 else [value[0] for value in d.layers.values()] if index == 1 else list(d.styles.values()) if index == 2 else [d.continuous] if index == 3 else list(d.appids.values()) if index == 7 else [d.dimstyle] if index == 8 else []
        def body(w, entries=entries, index=index):
            w.bl(len(entries))
            if index == 8:
                w.rc(0)
        refs = [(2, item) for item in entries]
        if index == 0:
            refs += [(3, d.model), (3, d.paper)]
        if index == 3:
            refs += [(3, d.byblock), (3, d.bylayer)]
        add(typ, handle, 0, body, refs)
    for name, handle in d.appids.items():
        def appid(w, name=name):
            table_name(w, name)
            w.rc(0)
        add(0x43, handle, d.controls[7], appid, [(5, 0)])
    nod, groups, mlines, layouts, plots, styles = d.dictionaries
    for index, handle in enumerate(d.dictionaries):
        names = ("ACAD_GROUP", "ACAD_MLINESTYLE", "ACAD_LAYOUT", "ACAD_PLOTSETTINGS", "ACAD_PLOTSTYLENAME") if index == 0 else ("Model", "Layout1") if index == 3 else ("Normal",) if index == 5 else ()
        values = (groups, mlines, layouts, plots, styles) if index == 0 else (d.model_layout, d.paper_layout) if index == 3 else (d.normal_plotstyle,) if index == 5 else ()
        if index == 0:
            names += tuple(d.named_objects)
            values += tuple(d.named_objects.values())
        def body(w, names=names):
            w.bl(len(names))
            w.bs(1)
            w.rc(0)
            for name in names:
                w.text(name)
        refs = [(2, item) for item in values] + ([(5, d.normal_plotstyle)] if index == 5 else [])
        add(500 if index == 5 else 0x2A, handle, 0 if index == 0 else nod, body, refs)
    add(501, d.normal_plotstyle, styles, lambda w: None)
    for name, (handle, color, visible) in d.layers.items():
        def body(w, name=name, color=color, visible=visible):
            table_name(w, name)
            w.bs(16 | 29 << 5 | (0 if visible else 2))
            w.bs(color)
        add(0x33, handle, d.controls[1], body, [(5, 0), (5, d.normal_plotstyle), (5, d.continuous)])
    def dimstyle(w):
        table_name(w, "Standard")
        w.text("")
        w.text("")
        dimensions(w)
        w.b(0)
    add(0x45, d.dimstyle, d.controls[8], dimstyle, [(5, 0), (5, d.style), (5, 0), (5, 0), (5, 0), (5, 0)])
    for name, handle in d.styles.items():
        def body(w, name=name):
            table_name(w, name)
            w.b(0)
            w.b(0)
            for value in (0.0, 1.0, 0.0):
                w.bd(value)
            w.rc(0)
            w.bd(2.5)
            w.text("txt.shx")
            w.text("")
        add(0x35, handle, d.controls[2], body, [(5, 0)])
    for name, handle in (("BYLAYER", d.bylayer), ("BYBLOCK", d.byblock), ("CONTINUOUS", d.continuous)):
        def body(w, name=name):
            table_name(w, name)
            w.text("")
            w.bd(0.0)
            w.rc(65)
            w.rc(0)
            w.raw(bytes(256))
        add(0x39, handle, d.controls[3], body, [(5, 0)])
    spaces = [(d.model, "*Model_Space", d.model_begin, d.model_end, [e.handle for e in d.entities], d.model_layout), (d.paper, "*Paper_Space", d.paper_begin, d.paper_end, [], d.paper_layout)]
    spaces += [(handle, name, begin, end, [e.handle for e in d.block_entities[handle]], 0) for name, (handle, begin, end) in d.blocks.items()]
    for handle, name, begin, end, contents, layout in spaces:
        def body(w, name=name):
            table_name(w, name)
            for _ in range(5):
                w.b(0)
            w.point((0.0, 0.0, 0.0))
            w.text("")
            w.rc(0)
            w.text("")
            w.bl(0)
        refs = [(5, 0), (3, begin), (4, contents[0] if contents else 0), (4, contents[-1] if contents else 0), (3, end), (5, layout)]
        result.append((handle, object_payload(0x31, handle, d.controls[0], body, refs, xdata=d.block_xdata.get(handle, ()))))
        if layout:
            add(502, layout, layouts, lambda w, name="Model" if handle == d.model else "Layout1": layout_body(w, name), [(4, handle), (4, 0), (5, 0), (5, 0)])
        for entity_handle, typ in ((begin, 4), (end, 5)):
            entity = Entity(entity_handle, typ, "0", (lambda w, name=name: w.text(name)) if typ == 4 else (lambda w: None), owner=handle)
            result.append((entity_handle, entity_payload(entity, d)))
    return result


def ucs(w):
    w.bd(0.0)
    for point in ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)):
        w.point(point)
    w.handle(5, 0)
    w.handle(5, 0)
    w.bs(0)
    w.handle(5, 0)
    for _ in range(6):
        w.point((0.0, 0.0, 0.0))


def section(sentinel, data):
    payload = struct.pack("<I", len(data)) + data
    return sentinel + payload + struct.pack("<H", crc16(payload)) + bytes(value ^ 255 for value in sentinel)


def header_section(d):
    w = BitWriter()
    for value in (412148564080.0, 1.0, 1.0, 1.0):
        w.bd(value)
    for _ in range(4):
        w.text("")
    w.bl(24)
    w.bl(0)
    w.handle(5, 0)
    for value in (1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 1, 0, 0):
        w.b(value)
    for value in (1, 3020, 2, 4, 0, 4, 1, 0, 0, 0, 0, 0, 0, 8, 6, 6, 6, 6, 6, 6, 3, 70, 0, 64, 4, 0, 50):
        w.bs(value)
    for value in (1.0, 2.5, 1.0, 1.0, *([0.0] * 14), 0.5, 1.0, 1.0):
        w.bd(value)
    w.text("")
    for value in (2451545, 0, 2451545, 0, 0, 0, 0, 0):
        w.bl(value)
    w.bs(256)
    w.handle(0, d.next_handle)
    for handle in (d.layer, d.style, d.bylayer, d.dimstyle, 0):
        w.handle(5, handle)
    w.bd(0.0)
    for points in (((0.0, 0.0, 0.0),) * 3, ((0.0, 0.0, 0.0), *d.extents)):
        for point in points:
            w.point(point)
        for value in (0.0, 0.0, 420.0, 297.0):
            w.rd(value)
        ucs(w)
    w.text("")
    w.text("")
    dimensions(w, d.style)
    for handle in d.controls:
        w.handle(3, handle)
    for code, handle in ((5, d.dictionaries[1]), (5, d.dictionaries[2]), (3, d.dictionaries[0])):
        w.handle(code, handle)
    w.bs(1)
    w.bs(70)
    w.text("")
    w.text("")
    for handle in d.dictionaries[3:]:
        w.handle(5, handle)
    w.bl(0x2A1D)
    w.bs(4)
    w.bs(0)
    w.text("")
    w.text("")
    for handle in (d.paper, d.model, d.bylayer, d.byblock, d.continuous):
        w.handle(5, handle)
    for _ in range(4):
        w.bs(0)
    return section(HEADER_SENTINEL, w.finish())


def classes_section(classes):
    w = BitWriter()
    for item in classes:
        w.bs(item.number)
        w.bs(item.proxy_flags)
        w.text(item.application)
        w.text(item.cpp_name)
        w.text(item.name)
        w.b(0)
        w.bs(0x1F2 if item.entity else 0x1F3)
    return section(CLASSES_SENTINEL, w.finish())


def object_map(entries):
    output = bytearray()
    payload = bytearray()
    previous_handle = previous_offset = 0
    def flush():
        block = struct.pack(">H", len(payload) + 2) + payload
        output.extend(block + struct.pack(">H", crc16(block)))
    for handle, offset in sorted(entries):
        pair = modular_char(handle - previous_handle) + modular_char(offset - previous_offset)
        if len(payload) + len(pair) + 2 > 2032:
            flush()
            payload.clear()
            pair = modular_char(handle) + modular_char(offset)
        payload.extend(pair)
        previous_handle, previous_offset = handle, offset
    if payload:
        flush()
        payload.clear()
    flush()
    return bytes(output)


def encode_container(drawing, rows):
    if len({handle for handle, _ in rows}) != len(rows):
        raise ValueError("Drawing objects require unique handles")
    header = header_section(drawing)
    classes = classes_section(drawing.classes)
    output = bytearray(72)
    output[:6] = b"AC1015"
    output[0x0C] = 1
    output[0x11:0x13] = bytes((0x17, 0x0F))
    struct.pack_into("<HI", output, 0x13, 39, 3)
    header_offset = len(output)
    output.extend(header)
    classes_offset = len(output)
    output.extend(classes)
    output.extend(bytes(512))
    output.extend(bytes(-len(output) % 4))
    entries = []
    for handle, payload in sorted(rows):
        entries.append((handle, len(output)))
        record = modular_short(len(payload)) + payload
        output.extend(record + struct.pack("<H", crc16(record)))
    output.extend(bytes(-len(output) % 4))
    map_offset = len(output)
    mapping = object_map(entries)
    output.extend(mapping)
    position = 0x19
    for number, offset, size in ((0, header_offset, len(header)), (1, classes_offset, len(classes)), (2, map_offset, len(mapping))):
        struct.pack_into("<BII", output, position, number, offset, size)
        position += 9
    struct.pack_into("<H", output, position, crc16(output[:position], 0) ^ 0xA598)
    output[position + 2:position + 18] = DIRECTORY_SENTINEL
    return bytes(output)


def inspect_container(data):
    if data[:6] != b"AC1015" or len(data) < 72:
        raise ValueError("Native DWG readback requires a complete AC1015 drawing")
    count = struct.unpack_from("<I", data, 0x15)[0]
    if count != 3:
        raise ValueError("Native DWG readback requires the three-section directory")
    end = 0x19 + count * 9
    if struct.unpack_from("<H", data, end)[0] != crc16(data[:end], 0) ^ 0xA598 or data[end + 2:end + 18] != DIRECTORY_SENTINEL:
        raise ValueError("The drawing directory requires a matching checksum and sentinel")
    sections = {}
    for position in range(0x19, end, 9):
        number, offset, size = struct.unpack_from("<BII", data, position)
        if offset < 72 or offset + size > len(data) or number in sections:
            raise ValueError("Drawing sections require unique bounded ranges")
        sections[number] = (offset, size)
    if set(sections) != {0, 1, 2}:
        raise ValueError("Drawing sections require header, classes and object-map identities")
    ranges = sorted((offset, offset + size) for offset, size in sections.values())
    if any(first[1] > second[0] for first, second in zip(ranges, ranges[1:])):
        raise ValueError("Drawing sections require disjoint file ranges")
    for number, sentinel in ((0, HEADER_SENTINEL), (1, CLASSES_SENTINEL)):
        offset, size = sections[number]
        if size < 38:
            raise ValueError("Drawing sections require complete sentinel and size fields")
        part = data[offset:offset + size]
        length = struct.unpack_from("<I", part, 16)[0]
        if size != length + 38 or part[:16] != sentinel or part[-16:] != bytes(item ^ 255 for item in sentinel) or struct.unpack_from("<H", part, size - 18)[0] != crc16(part[16:size - 18]):
            raise ValueError("Drawing sections require matching lengths, checksums and sentinels")
    entries = []
    offset, size = sections[2]
    position, length = offset, 0
    pages = 0
    while position < offset + size:
        if position + 4 > offset + size:
            raise ValueError("Object-map pages require complete length and checksum fields")
        length = struct.unpack_from(">H", data, position)[0]
        if length < 2 or length > 2032 or position + length + 2 > offset + size:
            raise ValueError("Object-map pages require bounded lengths")
        if struct.unpack_from(">H", data, position + length)[0] != crc16(data[position:position + length]):
            raise ValueError("Object-map pages require matching checksums")
        current = position + 2
        handle = record_offset = 0
        while current < position + length:
            delta, current = read_modular_char(data, current, position + length)
            handle += delta
            delta, current = read_modular_char(data, current, position + length)
            record_offset += delta
            entries.append((handle, record_offset))
        position += length + 2
        if length == 2:
            break
        pages += 1
    if position != offset + size or length != 2:
        raise ValueError("Object maps require a terminal page and exact section coverage")
    objects = []
    previous_end = sections[1][0] + sections[1][1]
    for handle, record_offset in entries:
        if handle <= 0 or record_offset < previous_end or record_offset + 2 > offset:
            raise ValueError("Object records require positive identities and bounded file ranges")
        first = struct.unpack_from("<H", data, record_offset)[0]
        prefix = 4 if first & 0x8000 else 2
        length = first & 0x7FFF
        if prefix == 4:
            if record_offset + 4 > offset:
                raise ValueError("Object sizes require a complete modular prefix")
            length |= struct.unpack_from("<H", data, record_offset + 2)[0] << 15
        stop = record_offset + prefix + length
        if record_offset < previous_end or stop + 2 > offset:
            raise ValueError("Object records require ordered bounded file ranges")
        if struct.unpack_from("<H", data, stop)[0] != crc16(data[record_offset:stop]):
            raise ValueError("Object records require matching checksums")
        body = data[record_offset + prefix:stop]
        reader = BitReader(body)
        typ = reader.bs()
        data_bits = reader.rl()
        code, identity = reader.handle()
        if code != 0 or identity != handle or data_bits > len(body) * 8 or data_bits < reader.position:
            raise ValueError("Object headers require matching identities and bounded streams")
        objects.append({"handle": handle, "type_code": typ, "offset": record_offset, "data_bits": data_bits, "body": body})
        previous_end = stop + 2
    if len({item['handle'] for item in objects}) != len(objects):
        raise ValueError("Object maps require unique identities")
    return {"version": "AC1015", "sections": sections, "map_pages": pages, "objects": objects}
