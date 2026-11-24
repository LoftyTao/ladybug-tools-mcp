"""Transient THMZ result members and node-level moisture fields.

Pure-Python reader/writer for both the pyHygroThermFEM-Fairyfly-owned and THERM 8.1.30.0
``transient results/`` layouts, plus an own XML path for
``SteadyStateMeshResults.xml`` node fields the pylibraryfemtherm binding does
not expose (``Humidity``/``WaterContent``).

Owned APIs keep their slash separators, scalar columns and initial frame.
The explicit ``therm_*``/``read_therm_*`` APIs use the three THERM table
shapes verified against THERM 8.1 reference archives. The THERM ZIP writer
mirrors backslash separators only for its eight result members. Its vector
writer requires explicitly declared signed Geometry-coordinate components;
it never guesses components from a magnitude or unknown coordinate frame.
In the owned layout, the first column is the step time in seconds,
remaining columns are one scalar per entity whose header carries the
``Geometry.xml`` node/edge ``ID``. Contract violations raise the
``errors.make_error`` family (``ContractError`` subclasses that remain
``ValueError``) carrying ``THMZ-Exxxx`` codes.

Writer labels accept integers, integral finite numbers such as 1.0, and
integer text accepted by int(). Fractional values, booleans, missing values
and non-finite values are rejected rather than truncated. Zero and negative
integer labels are not newly restricted here.
"""
import csv
from dataclasses import dataclass
import io
import math
from numbers import Number
import xml.etree.ElementTree as ET

from .errors import make_error

TRANSIENT_RESULTS_DIR = 'transient results'
TRANSIENT_RESULT_MEMBERS = {
    'geometry': TRANSIENT_RESULTS_DIR + '/Geometry.xml',
    'temperatures': TRANSIENT_RESULTS_DIR + '/Temperatures.csv',
    'humidities': TRANSIENT_RESULTS_DIR + '/Humidities.csv',
    'heat_flux': TRANSIENT_RESULTS_DIR + '/HeatFlux.csv',
    'heat_flux_edges': TRANSIENT_RESULTS_DIR + '/HeatFluxEdges.csv',
    'water_content': TRANSIENT_RESULTS_DIR + '/WaterContent.csv',
    'water_flux': TRANSIENT_RESULTS_DIR + '/WaterFlux.csv',
    'water_flux_edges': TRANSIENT_RESULTS_DIR + '/WaterFluxEdges.csv',
}
THERM_TRANSIENT_RESULT_MEMBERS = {
    key: name.replace('/', '\\')
    for key, name in TRANSIENT_RESULT_MEMBERS.items()}

# Owned-layout step exchange members (contract 2.1, ADR-0010 option a).
# Each row carries the per-edge boundary exchange accumulated over the
# accepted sub-steps of the interval ending at that row's time: heat in J/m
# and water in kg/m, outward-positive per metre of depth, column order and
# entity IDs identical to the matching *Edges rate members. The t=0 initial
# frame writes zeros (no preceding interval exists). These members exist
# only in the owned layout; THERM 8.1.30.0 writes no such data and the THERM
# layout path must not require or emit them.
TRANSIENT_STEP_EXCHANGE_MEMBERS = {
    'heat_flux_step_exchange':
        TRANSIENT_RESULTS_DIR + '/HeatFluxStepExchange.csv',
    'water_flux_step_exchange':
        TRANSIENT_RESULTS_DIR + '/WaterFluxStepExchange.csv',
}

_THERM_KINDS = {
    'temperatures': 'scalar', 'humidities': 'scalar',
    'water_content': 'scalar', 'heat_flux': 'vector',
    'water_flux': 'vector', 'heat_flux_edges': 'edges',
    'water_flux_edges': 'edges'}

_XML_DECLARATION = '<?xml version="1.0" encoding="utf-8"?>\n'
# Owned layout time header; THERM tables have distinct step/vector/time axes.
_TIME_HEADER = 'Time (s)'


def _fail(code, message):
    raise make_error(code, message)


def _parse_xml(content, member):
    if isinstance(content, str):
        content = content.encode('utf-8')
    if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
        _fail('THMZ-E1005', '{}: XML entities are not supported'.format(
            member))
    try:
        return ET.fromstring(content)
    except ET.ParseError as error:
        _fail('THMZ-E2000', '{}: {}'.format(member, error))


def _num(value):
    return str(int(value)) if float(value).is_integer() else repr(
        float(value))


def _serialize(parent, tag, value):
    child = ET.SubElement(parent, tag)
    child.text = value
    return child


# --- transient results/Geometry.xml -----------------------------------------

def geometry_to_xml(geometry):
    """Serialize geometry dict to ``InputGeometryData`` XML (str).

    Args:
        geometry: Dict with ``materials``, ``nodes``, ``elements``,
            ``material_polygons`` and ``model_enclosure`` keys. Records are
            dicts using ``id``, ``name``, ``color``, ``x``, ``y``,
            ``node_ids`` (four-tuple) and ``material_id``. Coordinates use
            metres; integer IDs are labels, not position indices. Integral
            numbers such as 1.0 and integer text are accepted without loss;
            booleans, missing/non-finite values and fractions are rejected.

    Returns:
        XML text with an ``InputGeometryData`` root and ``Version=1``.

    Raises:
        ContractError: ``THMZ-E2000`` for invalid/duplicate node/material
            labels, invalid corner counts or non-finite coordinates.
        MeshError: ``THMZ-E3000`` for unknown element node/material references.

    IDs are integer labels and references, not sequence positions. The
    release archive's mapping to Mesh.xml remains unverified.
    """
    context = TRANSIENT_RESULT_MEMBERS['geometry']
    node_ids = [_int_value(node['id'], 'Nodes/Node/ID', context)
                for node in geometry.get('nodes', ())]
    if len(set(node_ids)) != len(node_ids):
        _fail('THMZ-E2000', '{}: duplicate node ID'.format(context))
    node_id_set = set(node_ids)
    material_ids = [_int_value(m['id'], 'Materials/Material/ID', context)
                    for m in geometry.get('materials', ())]
    if len(set(material_ids)) != len(material_ids):
        _fail('THMZ-E2000', '{}: duplicate material ID'.format(context))
    material_id_set = set(material_ids)

    root = ET.Element('InputGeometryData')
    _serialize(root, 'Version', '1')
    materials = ET.SubElement(root, 'Materials')
    for material in geometry.get('materials', ()):
        element = ET.SubElement(materials, 'Material')
        _serialize(element, 'ID', str(_int_value(
            material['id'], 'Materials/Material/ID', context)))
        _serialize(element, 'Name', material['name'])
        _serialize(element, 'Color', material['color'])
    nodes = ET.SubElement(root, 'Nodes')
    for node in geometry.get('nodes', ()):
        element = ET.SubElement(nodes, 'Node')
        _serialize(element, 'ID', str(_int_value(
            node['id'], 'Nodes/Node/ID', context)))
        for key in ('x', 'y'):
            value = node[key]
            if not math.isfinite(value):
                _fail('THMZ-E2000', '{}: node {} {} is not finite'.format(
                    context, node['id'], key))
            _serialize(element, key, _num(value))
    elements = ET.SubElement(root, 'Elements')
    for record in geometry.get('elements', ()):
        element = ET.SubElement(elements, 'Element')
        _serialize(element, 'ID', str(_int_value(
            record['id'], 'Elements/Element/ID', context)))
        corners = tuple(record['node_ids'])
        if len(corners) != 4:
            _fail('THMZ-E2000', '{}: element {} requires four NodeID'.format(
                context, record['id']))
        for corner in corners:
            corner = _int_value(corner, 'Elements/Element/NodeID', context)
            if corner not in node_id_set:
                _fail('THMZ-E3000', '{}: element {} references unknown node '
                      '{}'.format(context, record['id'], corner))
            _serialize(element, 'NodeID', str(corner))
        material_id = _int_value(
            record['material_id'], 'Elements/Element/MaterialID', context)
        if material_id_set and material_id not in material_id_set:
            _fail('THMZ-E3000', '{}: element {} references unknown material '
                  '{}'.format(context, record['id'], material_id))
        _serialize(element, 'MaterialID', str(material_id))
    polygons = ET.SubElement(root, 'MaterialPolygons')
    for polygon in geometry.get('material_polygons', ()):
        element = ET.SubElement(polygons, 'MaterialPolygon')
        _serialize(element, 'ID', str(_int_value(
            polygon['id'], 'MaterialPolygons/MaterialPolygon/ID', context)))
        _serialize(element, 'MaterialID', str(_int_value(
            polygon['material_id'],
            'MaterialPolygons/MaterialPolygon/MaterialID', context)))
        corners = tuple(polygon['node_ids'])
        if len(corners) < 3:
            _fail('THMZ-E2000', '{}: material polygon {} requires at least '
                  'three NodeID'.format(context, polygon['id']))
        for corner in corners:
            parsed = _int_value(
                corner, 'MaterialPolygons/MaterialPolygon/NodeID', context)
            if parsed not in node_id_set:
                _fail('THMZ-E3000', '{}: MaterialPolygons/MaterialPolygon/'
                      'NodeID references unknown node {!r}; actual node '
                      'IDs={!r}'.format(context, corner, sorted(node_id_set)))
            _serialize(element, 'NodeID', str(parsed))
    enclosure = ET.SubElement(root, 'ModelEnclosure')
    for node_id in geometry.get('model_enclosure', ()):
        parsed = _int_value(node_id, 'ModelEnclosure/NodeID', context)
        if parsed not in node_id_set:
            _fail('THMZ-E3000', '{}: ModelEnclosure/NodeID references '
                  'unknown node {!r}; actual node IDs={!r}'.format(
                      context, node_id, sorted(node_id_set)))
        _serialize(enclosure, 'NodeID', str(parsed))
    return _XML_DECLARATION + ET.tostring(root, encoding='unicode')


def check_geometry_node_references(root, member, node_ids):
    """Reject polygon/enclosure node references outside the node domain.

    Args:
        root: Parsed ``InputGeometryData`` element.
        member: Result member name kept verbatim in error messages (raw
            separators preserved).
        node_ids: Iterable of the actual ``Nodes/Node/ID`` labels.

    Raises:
        MeshError: ``THMZ-E3000`` naming the member, field path, raw value,
            enclosing element and the actual node ID domain.
    """
    node_domain = set(node_ids)
    for path in ('MaterialPolygons/MaterialPolygon', 'ModelEnclosure'):
        for parent in root.findall(path):
            for index, reference in enumerate(parent.findall('NodeID'), 1):
                # Integer syntax is validated by the geometry reader; keep
                # the source text in errors, never the parsed label alone.
                node_id = int(reference.text)
                if node_id not in node_domain:
                    _fail('THMZ-E3000',
                          '{}: {}/NodeID[{}]={!r} ({} ID {!r}) references '
                          'unknown node {!r}; actual node IDs={!r}'.format(
                              member, path, index, reference.text,
                              parent.tag, parent.findtext('ID'), node_id,
                              sorted(node_domain)))


def _int_field(element, tag, context):
    return _int_value(element.findtext(tag), tag, context)


def _int_value(text, field, context):
    message = '{}: {} {!r} must be an integer without loss'.format(
        context, field, text)
    if isinstance(text, bool) or not isinstance(text, (Number, str)):
        _fail('THMZ-E2000', message)
    try:
        value = int(text)
    except (TypeError, ValueError, OverflowError):
        _fail('THMZ-E2000', message)
    if isinstance(text, Number) and text != value:
        _fail('THMZ-E2000', message)
    return value


def _float_field(element, tag, context):
    text = element.findtext(tag)
    try:
        value = float(text)
    except (TypeError, ValueError):
        _fail('THMZ-E2000', '{}: {} must be a finite number'.format(
            context, tag))
    if not math.isfinite(value):
        _fail('THMZ-E2000', '{}: {} must be a finite number'.format(
            context, tag))
    return value


def read_geometry_xml(content, member=None):
    """Parse ``transient results/Geometry.xml`` into the geometry dict.

    Args:
        content: XML bytes or text in the current ``InputGeometryData``
            layout. Coordinates use metres and IDs are integer labels.
        member: Optional result member name kept verbatim in error
            messages (raw separators preserved); defaults to the owned
            ``transient results/Geometry.xml`` name.

    Returns:
        Dict with ``materials``, ``nodes``, ``elements``,
        ``material_polygons`` and ``model_enclosure`` records.

    Raises:
        ContractError: ``THMZ-E1005`` for XML entities; ``THMZ-E2000`` for
            malformed XML, wrong root, missing Version, invalid numeric
            fields or corner counts.
        MeshError: ``THMZ-E3000`` for unknown element node/material references.
    """
    context = member or TRANSIENT_RESULT_MEMBERS['geometry']
    root = _parse_xml(content, context)
    if root.tag != 'InputGeometryData':
        _fail('THMZ-E2000', '{}: expected InputGeometryData root'.format(
            context))
    if root.find('Version') is None:
        _fail('THMZ-E2000', '{}: missing Version'.format(context))
    geometry = {'materials': [], 'nodes': [], 'elements': [],
                'material_polygons': [], 'model_enclosure': ()}
    for element in root.findall('Materials/Material'):
        geometry['materials'].append({
            'id': _int_field(element, 'ID', context),
            'name': element.findtext('Name') or '',
            'color': element.findtext('Color') or ''})
    for element in root.findall('Nodes/Node'):
        geometry['nodes'].append({
            'id': _int_field(element, 'ID', context),
            'x': _float_field(element, 'x', context),
            'y': _float_field(element, 'y', context)})
    node_id_set = {node['id'] for node in geometry['nodes']}
    material_id_set = {m['id'] for m in geometry['materials']}
    for element in root.findall('Elements/Element'):
        try:
            corners = tuple(int(node.text) for node in
                            element.findall('NodeID'))
        except (TypeError, ValueError):
            _fail('THMZ-E2000', '{}: NodeID must be an integer'.format(
                context))
        if len(corners) != 4:
            _fail('THMZ-E2000', '{}: element requires four NodeID'.format(
                context))
        for corner in corners:
            if corner not in node_id_set:
                _fail('THMZ-E3000', '{}: element references unknown node '
                      '{}'.format(context, corner))
        material_id = _int_field(element, 'MaterialID', context)
        if material_id_set and material_id not in material_id_set:
            _fail('THMZ-E3000', '{}: element references unknown material '
                  '{}'.format(context, material_id))
        geometry['elements'].append({
            'id': _int_field(element, 'ID', context),
            'node_ids': corners,
            'material_id': material_id})
    for element in root.findall('MaterialPolygons/MaterialPolygon'):
        corners = tuple(_int_value(
            node.text, 'MaterialPolygons/MaterialPolygon/NodeID', context)
            for node in element.findall('NodeID'))
        if len(corners) < 3:
            _fail('THMZ-E2000', '{}: material polygon requires at least three '
                  'NodeID'.format(context))
        geometry['material_polygons'].append({
            'id': _int_field(element, 'ID', context),
            'material_id': _int_field(element, 'MaterialID', context),
            'node_ids': corners})
    model_enclosure = tuple(
        _int_value(node.text, 'ModelEnclosure/NodeID', context)
        for node in root.findall('ModelEnclosure/NodeID'))
    # Polygon and enclosure references must name actual nodes; the shared
    # checker keeps the raw member name and field path in diagnostics.
    check_geometry_node_references(root, context, node_id_set)
    geometry['model_enclosure'] = model_enclosure
    return geometry


# --- transient results/*.csv -------------------------------------------------

def _parse_entity(label, context):
    try:
        return int(label)
    except (TypeError, ValueError):
        _fail('THMZ-E2000', '{}: column label {!r} is not an entity ID'
              .format(context, label))


def read_transient_series(content):
    """Parse one ``transient results/*.csv`` member.

    Args:
        content: UTF-8 CSV bytes (an optional BOM is accepted) or CSV text
            in the owned ``Time (s)`` layout. Time is in seconds; node
            temperatures are in degrees Celsius, relative humidity is
            dimensionless, and water content is in kg/m³. Heat flux
            densities are in W/m² and edge heat rates are in W/m. The
            reader preserves values without unit conversion or clipping.

    Returns:
        Dict with ``labels`` (trimmed header), ``entities`` (tuple of int IDs),
        ``times`` (list of seconds) and ``values`` (list of row lists).
        This convenience reader materializes the whole series in memory;
        it is not a bounded-memory reader. See the module docstring for
        the layout's ownership and release-evidence limits.

    Raises:
        ContractError: ``THMZ-E2000`` for invalid UTF-8, malformed headers,
            row lengths, non-numeric/non-finite values or decreasing times.
    """
    context = 'transient results csv'
    if isinstance(content, bytes):
        try:
            content = content.decode('utf-8-sig')
        except UnicodeDecodeError as error:
            _fail('THMZ-E2000', '{}: invalid UTF-8: {}'.format(context, error))
    rows = list(csv.reader(io.StringIO(content)))
    if not rows or not rows[0]:
        _fail('THMZ-E2000', '{}: empty result file'.format(context))
    header = [cell.strip() for cell in rows[0]]
    if len(header) < 2 or not header[0].lower().startswith('time'):
        _fail('THMZ-E2000', '{}: first column must be the time axis'.format(
            context))
    entities = tuple(_parse_entity(cell, context) for cell in header[1:])
    times, values = [], []
    previous = -math.inf
    for row in rows[1:]:
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) != len(header):
            _fail('THMZ-E2000', '{}: row has {} cells, expected {}'.format(
                context, len(row), len(header)))
        try:
            time = float(row[0])
        except ValueError:
            _fail('THMZ-E2000', '{}: invalid time {!r}'.format(
                context, row[0]))
        if not math.isfinite(time) or time < previous:
            _fail('THMZ-E2000', '{}: times must be finite and non-decreasing'
                  .format(context))
        previous = time
        try:
            row_values = [float(cell) for cell in row[1:]]
        except ValueError:
            _fail('THMZ-E2000', '{}: non-numeric cell in row at {}'.format(
                context, time))
        if not all(math.isfinite(value) for value in row_values):
            _fail('THMZ-E2000', '{}: non-finite value at {}'.format(
                context, time))
        times.append(time)
        values.append(row_values)
    return {'labels': header, 'entities': entities,
            'times': times, 'values': values}


class TransientSeriesWriter:
    """Append-only CSV writer emitting one row per completed timestep.

    For a fixed entity count, state is independent of the number of steps.
    Each step emits one row and flushes the target text stream. Caller-owned
    streams remain open when the writer closes.
    This writes the owned layout, not a verified THERM release format.
    """

    def __init__(self, path_or_stream, entities, time_header=_TIME_HEADER):
        """Open the target and record the entity column labels.

        Args:
            path_or_stream: File path or text stream accepting ``write``
                and ``flush``. Caller-owned streams are never closed.
            entities: Entity IDs (node or edge IDs) in column order. Whole
                numbers and integer text are accepted without loss;
                booleans, missing/non-finite values and fractions are rejected.
            time_header: Time-axis column label; defaults to ``Time (s)``.

        Raises:
            ContractError: ``THMZ-E2000`` for empty or invalid entity IDs.
        """
        self._entities = tuple(_int_value(
            value, 'entity ID', 'transient results csv') for value in entities)
        if not self._entities:
            _fail('THMZ-E2000',
                  'transient series requires at least one entity')
        self._header = [time_header] + [str(e) for e in self._entities]
        self._previous = -math.inf
        self._owns_stream = not hasattr(path_or_stream, 'write')
        if self._owns_stream:
            self._stream = open(path_or_stream, 'w', newline='')
        else:
            self._stream = path_or_stream
        self._writer = csv.writer(self._stream)
        self._started = False

    def write_step(self, time, values):
        """Append and flush one completed timestep row.

        Args:
            time: Finite, non-decreasing step time in seconds.
            values: Iterable of finite scalar values in entity order.
                Temperature uses degrees Celsius, relative humidity is
                dimensionless, and water content uses kg/m³. Values retain
                the supplied field units without conversion or clipping.

        Returns:
            None. The row is visible to readers after the stream is flushed.

        Raises:
            ContractError: ``THMZ-E2000`` for decreasing/non-finite times,
                incorrect value count or non-finite values.
        """
        if self._started and time < self._previous:
            _fail('THMZ-E2000',
                  'transient series times must be non-decreasing')
        values = list(values)
        if len(values) != len(self._entities):
            _fail('THMZ-E2000', 'transient step has {} values, expected {}'
                  .format(len(values), len(self._entities)))
        for value in values:
            if not math.isfinite(value):
                _fail('THMZ-E2000', 'transient step contains a non-finite '
                      'value')
        if not self._started:
            self._writer.writerow(self._header)
            self._started = True
        if not math.isfinite(time):
            _fail('THMZ-E2000', 'transient step time must be finite')
        self._previous = time
        self._writer.writerow([_num(time)] + [_num(v) for v in values])
        self._stream.flush()

    def close(self):
        """Close an owned file handle, leaving caller-owned streams open."""
        if self._owns_stream:
            self._stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def save_transient_series(entities, steps, time_header=_TIME_HEADER):
    """Render a whole series to CSV bytes (buffered convenience wrapper).

    Args:
        entities: Entity IDs in column order.
        steps: Iterable of ``(time_seconds, values)`` pairs; field units
            are those of ``TransientSeriesWriter.write_step``.
        time_header: Time-axis column label, defaulting to ``Time (s)``.

    Returns:
        UTF-8 CSV bytes containing all supplied steps.

    Raises:
        ContractError: ``THMZ-E2000`` for empty entity IDs or invalid steps.

    Use ``TransientSeriesWriter`` with a file path for bounded-memory
    output; this wrapper retains all output bytes in memory.
    """
    stream = io.StringIO()
    writer = TransientSeriesWriter(stream, entities, time_header=time_header)
    for time, values in steps:
        writer.write_step(time, values)
    return stream.getvalue().encode('utf-8')


def transient_result_members(geometry, series):
    """Assemble the ``transient results/`` member map for archive writes.

    Args:
        geometry: Geometry dict passed to :func:`geometry_to_xml`.
        series: Mapping of result key (one of ``temperatures``,
            ``humidities``, ``heat_flux``, ``heat_flux_edges``,
            ``water_content``, ``water_flux``, ``water_flux_edges``) to
            ``(entities, steps)``; steps is an iterable of timestep pairs.

    Returns:
        Dict of member name to bytes ready for the archive writer; unknown
        keys raise a contract error. This convenience function buffers all
        member bytes, unlike file-backed ``TransientSeriesWriter`` output.

    Raises:
        ContractError: ``THMZ-E2000`` for unknown member keys, invalid
            geometry fields or invalid series values.
        MeshError: ``THMZ-E3000`` for unknown element node/material references.
    """
    members = {TRANSIENT_RESULT_MEMBERS['geometry']:
               geometry_to_xml(geometry).encode('utf-8')}
    for key, (entities, steps) in series.items():
        if key not in TRANSIENT_RESULT_MEMBERS or key == 'geometry':
            _fail('THMZ-E2000', 'unknown transient result member {!r}'.format(
                key))
        members[TRANSIENT_RESULT_MEMBERS[key]] = save_transient_series(
            entities, steps)
    return members


# --- THERM 8.1.30.0 result layout --------------------------------------------

def _therm_rows(content):
    """Decode strict CSV and reject malformed UTF-8 with the result code."""
    try:
        if isinstance(content, bytes):
            content = content.decode('utf-8-sig')
        rows = list(csv.reader(io.StringIO(content), strict=True))
    except (UnicodeDecodeError, csv.Error) as error:
        _fail('THMZ-E2000', 'THERM result CSV: {}'.format(error))
    if not rows or not rows[0]:
        _fail('THMZ-E2000', 'THERM result CSV: empty member')
    return rows


def _therm_numbers(cells, member, row, fields, column=1):
    """Parse finite result numbers without clipping or unit conversion."""
    def fail(index, reason):
        _fail('THMZ-E2000', '{}: row {}, column {}, field {!r}: {}; '
              'received {!r}'.format(member, row, column + index,
                                    fields[index], reason, cells[index]))

    values = []
    for index, cell in enumerate(cells):
        try:
            values.append(float(cell))
        except (ValueError, TypeError, OverflowError):
            fail(index, 'invalid number')
    for index, value in enumerate(values):
        if not math.isfinite(value):
            fail(index, 'non-finite number')
    return values


def read_therm_transient_series(content, *, member='THERM result CSV'):
    """Read a THERM 8.1.30.0 scalar, vector or empty edge-time CSV.

    Args:
        content: UTF-8 CSV bytes or text. Scalar columns are consecutive
            Geometry node IDs starting at 1; no initial frame is present.
            Temperatures use degrees Celsius, relative humidity is
            dimensionless, water content is kg/m³ and heat flux is W/m².
            Edge times/durations use seconds; water-flux units and the
            independent y-direction physical convention remain unverified.
        member: Member name for numeric error locations. Row and column
            numbers are 1-based CSV positions, including header rows.

    Returns:
        Dict with kind, labels, entities, steps, times, errors and values.
        Times is None for scalar/vector fields: step IDs are not seconds.
        Vector values are signed (x, y) pairs, never magnitudes. Edge tables
        additionally return durations and contain no physical edge rates.

    Raises:
        ContractError: THMZ-E2000 for invalid headers, numbers or step IDs.
    """
    rows = _therm_rows(content)
    header = [cell.strip() for cell in rows[0]]
    if header == ['Total time', 'Timestep time', '']:
        if (len(rows) < 3 or rows[1] != ['sec', 'sec', ''] or
                rows[-1] != ['Total', '', '']):
            _fail('THMZ-E2000', 'THERM edge CSV: missing units or Total row')
        times, durations = [], []
        previous = 0.0
        for row_number, row in enumerate(rows[2:-1], 3):
            if len(row) != 3 or row[2] != '':
                _fail('THMZ-E2000',
                      'THERM edge CSV: expected empty edge table')
            time, duration = _therm_numbers(
                row[:2], member, row_number, header[:2])
            if (duration <= 0 or time <= previous or not math.isclose(
                    time - previous, duration, rel_tol=1e-9, abs_tol=1e-6)):
                _fail('THMZ-E2000', '{}: row {}, column 1, field {!r}: '
                      'received {!r}; column 2, field {!r}: received {!r}; '
                      'inconsistent step times; previous total time {!r} s'
                      .format(member, row_number, header[0], row[0],
                              header[1], row[1], previous))
            times.append(time)
            durations.append(duration)
            previous = time
        return {'kind': 'edges', 'labels': header, 'entities': (),
                'steps': list(range(1, len(times) + 1)), 'times': times,
                'durations': durations, 'errors': None,
                'values': [[] for _ in times]}
    if header[0].endswith('-x'):
        entities = tuple(range(1, len(header) // 2 + 1))
        expected = ['{}-{}'.format(entity, axis)
                    for entity in entities for axis in ('x', 'y')]
        if header != expected:
            _fail('THMZ-E2000', 'THERM vector CSV: expected 1-x,1-y,..,N-y')
        values = []
        for row_number, row in enumerate(rows[1:], 2):
            if len(row) != len(header):
                _fail('THMZ-E2000', 'THERM vector CSV: incorrect row width')
            numbers = _therm_numbers(row, member, row_number, header)
            values.append(list(zip(numbers[::2], numbers[1::2])))
        return {'kind': 'vector', 'labels': header, 'entities': entities,
                'steps': list(range(1, len(values) + 1)), 'times': None,
                'errors': None, 'values': values}
    if header[:2] != ['timestep #', 'error tolerance'] or len(header) < 3:
        _fail('THMZ-E2000', 'THERM result CSV: invalid scalar header')
    entities = tuple(range(1, len(header) - 1))
    if header[2:] != [str(entity) for entity in entities]:
        _fail('THMZ-E2000', 'THERM result CSV: expected node IDs 1..N')
    values, errors, steps = [], [], []
    for step, row in enumerate(rows[1:], 1):
        if len(row) != len(header):
            _fail('THMZ-E2000', 'THERM result CSV: incorrect row width')
        context = '{}: row {}, column 1, field {!r}: received {!r}'.format(
            member, step + 1, header[0], row[0])
        if _int_value(row[0], header[0], context) != step:
            _fail('THMZ-E2000', '{}; expected consecutive steps (expected {})'
                  .format(context, step))
        numbers = _therm_numbers(row[1:], member, step + 1, header[1:], 2)
        steps.append(step)
        errors.append(numbers[0])
        values.append(numbers[1:])
    return {'kind': 'scalar', 'labels': header, 'entities': entities,
            'steps': steps, 'times': None, 'errors': errors, 'values': values}


class ThermTransientSeriesWriter:
    """Append a THERM scalar/vector/time table with bounded step memory.

    Args:
        path_or_stream: Text stream or file path. Caller streams stay open.
        entities: Consecutive Geometry node IDs 1..N, or () for edge tables.
        kind: 'scalar', 'vector' or 'edges'. Edge tables store only times.
        vector_convention: Required for vectors: 'geometry-xy-signed'
            explicitly asserts signed components along Geometry x/y axes.
            Magnitudes and unknown coordinate systems are never converted.
            Independent y-direction physics and water-flux units remain
            unverified; this declaration does not certify those semantics.
        member: Optional member name used in numeric errors. Defaults to the
            target path/stream name, or a kind-specific CSV description.

    Raises:
        ContractError: THMZ-E2000 for ambiguous vectors or invalid fields.
    """

    def __init__(self, path_or_stream, entities, kind,
                 *, vector_convention=None, member=None):
        self._entities = tuple(_int_value(
            value, 'node ID', 'THERM result CSV') for value in entities)
        if kind not in ('scalar', 'vector', 'edges'):
            _fail('THMZ-E2000', 'THERM result CSV: unknown table kind')
        if kind == 'edges':
            if self._entities:
                _fail('THMZ-E2000',
                      'THERM edge CSV: entity columns unsupported')
            header = ['Total time', 'Timestep time', '']
        else:
            if (not self._entities or self._entities !=
                    tuple(range(1, len(self._entities) + 1))):
                _fail('THMZ-E2000', 'THERM result CSV: expected node IDs 1..N')
            if kind == 'vector':
                if vector_convention != 'geometry-xy-signed':
                    _fail('THMZ-E2000', 'THERM vector CSV: ambiguous '
                          'coordinate or sign convention')
                header = ['{}-{}'.format(entity, axis)
                          for entity in self._entities for axis in ('x', 'y')]
            else:
                header = ['timestep #', 'error tolerance'] + [
                    str(entity) for entity in self._entities]
        self._owns_stream = not hasattr(path_or_stream, 'write')
        self._stream = (open(path_or_stream, 'w', encoding='utf-8', newline='')
                        if self._owns_stream else path_or_stream)
        self._writer = csv.writer(self._stream, lineterminator='\n')
        self._member = (member if member is not None else
                        str(path_or_stream) if self._owns_stream else
                        str(getattr(path_or_stream, 'name',
                                    'THERM {} CSV'.format(kind))))
        self._header = header
        self._kind = kind
        self._previous = 0.0
        self._step = 0
        self._closed = False
        self._writer.writerow(header)
        if kind == 'edges':
            self._writer.writerow(['sec', 'sec', ''])
        self._stream.flush()

    def write_step(self, time, values=(), error=None):
        """Flush a completed positive-time step; scalar error defaults to 0.

        Args:
            time: Positive, strictly increasing elapsed time in seconds.
                Initial frames must be filtered by the caller. Scalar and
                vector tables do not serialize this time as a column.
            values: Scalar node values or signed (x, y) pairs in entity
                order; empty for edge tables. Temperature is degrees
                Celsius, relative humidity is dimensionless, water content
                is kg/m³ and heat flux is W/m². Water-flux units and the
                independent y-direction physical convention are unverified.
                Supplied values retain their units and signs unchanged.
            error: Scalar convergence value, or None to write 0. The metric
                is caller-provided; equivalence to THERM's error estimator
                and its units remain unverified. Ignored for non-scalars.

        Returns:
            None. The completed row is visible after flushing the stream.

        Raises:
            ContractError: THMZ-E2000 for a closed writer, non-finite or
                non-numeric values, invalid counts/pairs, non-increasing
                times or an unrepresentable six-decimal edge time.
            OSError: The target cannot be written or flushed.
        """
        if self._closed:
            _fail('THMZ-E2000', 'THERM result CSV: writer is closed')
        row_number = self._step + (3 if self._kind == 'edges' else 2)
        received_time = time
        time = _therm_numbers([time], self._member, row_number, ['time'])[0]
        if time <= self._previous:
            _fail('THMZ-E2000', '{}: row {}, column 1, field {!r}: '
                  'positive increasing times required (no initial frame); '
                  'received {!r}; previous elapsed time {!r} s'.format(
                      self._member, row_number, 'time', received_time,
                      self._previous))
        try:
            values = list(values)
        except TypeError:
            _fail('THMZ-E2000', 'THERM result CSV: values must be iterable')
        if len(values) != len(self._entities):
            _fail('THMZ-E2000', 'THERM result CSV: incorrect value count')
        if self._kind == 'scalar':
            numbers = _therm_numbers(
                [0 if error is None else error] + values, self._member,
                row_number, self._header[1:], 2)
            row = [str(self._step + 1)] + [_num(v) for v in numbers]
        elif self._kind == 'vector':
            try:
                pairs = [tuple(pair) for pair in values]
            except TypeError:
                _fail('THMZ-E2000', 'THERM vector CSV: signed pairs required')
            if any(len(pair) != 2 for pair in pairs):
                _fail('THMZ-E2000', 'THERM vector CSV: signed pairs required')
            numbers = _therm_numbers(
                [v for pair in pairs for v in pair], self._member,
                row_number, self._header)
            row = [_num(v) for v in numbers]
        else:
            row = ['{:.6f}'.format(time),
                   '{:.6f}'.format(time - self._previous), '']
            represented_time, represented_duration = _therm_numbers(
                row[:2], self._member, row_number, self._header[:2])
            if (represented_time <= round(self._previous, 6) or
                    represented_duration <= 0):
                _fail('THMZ-E2000', 'THERM edge CSV: step time cannot be '
                      'represented at six decimals')
        self._writer.writerow(row)
        self._stream.flush()
        self._step += 1
        self._previous = time

    def close(self):
        """Finalize the edge Total row once; leave caller streams open.

        Returns:
            None. Repeated calls have no effect; no physical rates are added.

        Raises:
            OSError: The target cannot be written, flushed or closed.
        """
        if self._closed:
            return
        if self._kind == 'edges':
            self._writer.writerow(['Total', '', ''])
        self._stream.flush()
        self._closed = True
        if self._owns_stream:
            self._stream.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def read_therm_transient_results(members):
    """Read and cross-check all eight THERM result members from a mapping.

    Args:
        members: Mapping of slash/backslash member names to XML/CSV bytes or
            text. Diagnostics keep the original member name including any
            raw backslash separator. Geometry coordinates use metres;
            temperatures use degrees Celsius, relative humidity is
            dimensionless, water content is kg/m³, heat flux is W/m² and
            edge times/durations use seconds. Water-flux units and
            independent y-direction physics remain unverified. Values are
            not converted or physically certified.

    Returns:
        Dict with geometry and series mappings. Scalar/vector step IDs are
        not seconds. This convenience reader materializes all rows in memory.

    Raises:
        ContractError: THMZ-E1003 for normalized duplicate members, E1004 for
            missing members, E1005 for XML entities, or E2000 for invalid
            field kinds, numeric values, node domains, counts or time axes.
        MeshError: THMZ-E3000 for invalid geometry node/material references.
    """
    normalized = {}
    raw_names = {}
    for name, content in members.items():
        key = name.replace('\\', '/')
        if key in normalized:
            _fail('THMZ-E1003', 'duplicate normalized result member ' + key)
        normalized[key] = content
        raw_names[key] = name
    for name in TRANSIENT_RESULT_MEMBERS.values():
        if name not in normalized:
            _fail('THMZ-E1004', 'missing THERM result member ' + name)
    geometry = read_geometry_xml(
        normalized[TRANSIENT_RESULT_MEMBERS['geometry']],
        member=raw_names[TRANSIENT_RESULT_MEMBERS['geometry']])
    node_ids = tuple(node['id'] for node in geometry['nodes'])
    if (not node_ids or len(set(node_ids)) != len(node_ids) or
            set(node_ids) != set(range(1, len(node_ids) + 1))):
        _fail('THMZ-E2000', 'THERM geometry: expected unique node IDs 1..N')
    series = {}
    steps = None
    for key, kind in _THERM_KINDS.items():
        parsed = read_therm_transient_series(
            normalized[TRANSIENT_RESULT_MEMBERS[key]],
            member=TRANSIENT_RESULT_MEMBERS[key])
        if parsed['kind'] != kind or (kind != 'edges' and
                set(parsed['entities']) != set(node_ids)):
            _fail('THMZ-E2000', 'THERM result {}: field/node domain mismatch'
                  .format(key))
        if steps is None:
            steps = parsed['steps']
        if not steps or parsed['steps'] != steps:
            _fail('THMZ-E2000', 'THERM result {}: frame count mismatch'
                  .format(key))
        series[key] = parsed
    if (series['heat_flux_edges']['times'] !=
            series['water_flux_edges']['times']):
        _fail('THMZ-E2000', 'THERM result: edge time axes disagree')
    return {'geometry': geometry, 'series': series}


def therm_transient_result_members(geometry, frames,
                                   *, vector_convention=None):
    """Buffer all eight THERM layout members from native TransientFrame tuples.

    Args:
        geometry: Geometry dict with node order 1..N matching frame values.
            Coordinates use metres.
        frames: Native callback tuples (step, time, temperature, humidity,
            water_content, ice_content, heat_flux, water_flux, edge_heat_rates,
            edge_water_rates, edge_heat_exchange, edge_water_exchange,
            temperature_error, humidity_error). Step is
            zero-based; the optional step=-1/time=0 initial frame is omitted.
            Time is seconds, temperature is degrees Celsius, humidity is
            dimensionless, water content is kg/m³ and heat flux is W/m².
            Water-flux units, independent y-direction physics and THERM
            error-estimator equivalence/units remain unverified.
        vector_convention: Explicit 'geometry-xy-signed' assertion. Unknown
            coordinates and magnitudes are rejected, never guessed.

    Returns:
        Backslash-named bytes mapping. Scalar errors use temperature_error
        or humidity_error (also for water_content); None writes 0. Edge
        rates remain only in the owned layout, not in these empty tables.
        Use write_therm_transient_members for raw Windows ZIP separators.

    Raises:
        ContractError: THMZ-E2000 for invalid geometry/frames/conventions.
        MeshError: THMZ-E3000 for unknown geometry element node/material
            references propagated from geometry_to_xml.
    """
    xml = ET.fromstring(geometry_to_xml(geometry))
    xml.find('Version').text = None
    entities = tuple(node['id'] for node in geometry['nodes'])
    streams = {key: io.StringIO() for key in _THERM_KINDS}
    writers = {key: ThermTransientSeriesWriter(
        streams[key], () if kind == 'edges' else entities, kind,
        vector_convention=vector_convention,
        member=THERM_TRANSIENT_RESULT_MEMBERS[key])
        for key, kind in _THERM_KINDS.items()}
    count = 0
    initial_seen = False
    try:
        for frame in frames:
            try:
                (step, time, temperature, humidity, water_content, _ice,
                 heat_flux, water_flux, _edge_heat, _edge_water,
                 _edge_heat_exchange, _edge_water_exchange,
                 temperature_error, humidity_error) = frame
            except (ValueError, TypeError):
                _fail('THMZ-E2000',
                      'THERM result: invalid TransientFrame tuple')
            step = _int_value(step, 'step', 'THERM TransientFrame')
            if step == -1:
                if initial_seen or count or _therm_numbers(
                        [time], 'TransientFrame', count + 1, ['time'], 2)[0] != 0:
                    _fail('THMZ-E2000', 'THERM result: invalid initial frame')
                initial_seen = True
                continue
            if step != count:
                _fail('THMZ-E2000', 'THERM result: non-consecutive frame step')
            fields = {'temperatures': temperature, 'humidities': humidity,
                      'water_content': water_content, 'heat_flux': heat_flux,
                      'water_flux': water_flux}
            for key, writer in writers.items():
                error = (temperature_error if key == 'temperatures' else
                         humidity_error if key in
                         ('humidities', 'water_content')
                         else None)
                writer.write_step(time, fields.get(key, ()), error)
            count += 1
    finally:
        for writer in writers.values():
            writer.close()
    if not count:
        _fail('THMZ-E2000', 'THERM result: no completed frames')
    xml_text = _XML_DECLARATION + ET.tostring(xml, encoding='unicode')
    members = {THERM_TRANSIENT_RESULT_MEMBERS['geometry']:
               xml_text.encode('utf-8')}
    members.update({THERM_TRANSIENT_RESULT_MEMBERS[key]:
                    stream.getvalue().encode('utf-8')
                    for key, stream in streams.items()})
    return members


def write_therm_transient_members(archive, members):
    """Write a validated THERM member map with raw ZIP backslash separators.

    ZipInfo's Windows constructor normalizes separators. Assign the exact
    name after construction so both ZIP local and central headers mirror
    THERM. Only these eight result members are written; caller-owned input
    members and the archive handle are left unchanged and open.

    Args:
        archive: Open writable zipfile.ZipFile; remains caller-owned.
        members: Mapping of the eight exact backslash names to result bytes
            or text. Geometry coordinates use metres, temperatures degrees
            Celsius, relative humidity is dimensionless, water content is
            kg/m³, heat flux is W/m² and edge times/durations use seconds.
            Water-flux units and independent y-direction physics remain
            unverified. This function does not convert or certify units.

    Returns:
        None. The validated members are added without modifying input members.

    Raises:
        ContractError: THMZ-E1003 for duplicate/existing results, E1004 for
            missing members, E1005 for XML entities or E2000 for invalid
            names, structures, numeric values or cross-member consistency.
        MeshError: THMZ-E3000 for invalid geometry references.
        OSError: The archive cannot be written.
    """
    import zipfile
    read_therm_transient_results(members)
    expected = set(THERM_TRANSIENT_RESULT_MEMBERS.values())
    if set(members) != expected:
        _fail('THMZ-E2000',
              'THERM ZIP writer: expected eight backslash members')
    existing = {name.replace('\\', '/') for name in archive.namelist()}
    if existing.intersection(TRANSIENT_RESULT_MEMBERS.values()):
        _fail('THMZ-E1003', 'THERM ZIP writer: result members already exist')
    for name, content in members.items():
        info = zipfile.ZipInfo(name)
        info.filename = info.orig_filename = name
        info.compress_type = archive.compression
        archive.writestr(info, content)


# --- SteadyStateMeshResults.xml moisture fields ------------------------------

_NODE_FIELDS = ('Index', 'Temperature', 'X-flux', 'Y-flux', 'Humidity',
                'WaterContent')


def read_mesh_node_results(content):
    """Read ``SteadyStateMeshResults.xml`` nodes via the own XML path.

    Args:
        content: XML text or bytes containing a ``MeshResults`` root with
            exactly one ``Case``. Node temperatures use degrees Celsius,
            ``X-flux``/``Y-flux`` use W/m², relative humidity is
            dimensionless, and water content uses kg/m³.

    Returns:
        List of dicts with integer ``index`` and finite ``temperature``,
        ``x_flux`` and ``y_flux`` values. Optional ``humidity`` and
        ``water_content`` are None when absent. Values are not converted
        or clipped. This own path exposes the moisture fields that the
        pylibraryfemtherm binding does not expose.

    Raises:
        ContractError: ``THMZ-E1005`` for XML entities; ``THMZ-E2000`` for
            malformed XML, wrong root/case count, unknown node fields,
            missing/invalid numbers or duplicate node indices.
    """
    context = 'SteadyStateMeshResults.xml'
    root = _parse_xml(content, context)
    if root.tag != 'MeshResults':
        _fail('THMZ-E2000', '{}: expected MeshResults root'.format(context))
    cases = root.findall('Case')
    if len(cases) != 1:
        _fail('THMZ-E2000', '{}: expected exactly one Case'.format(context))
    nodes = []
    seen = set()
    for node in cases[0].findall('Nodes/Node'):
        tags = {child.tag for child in node}
        unknown = tags - set(_NODE_FIELDS)
        if unknown:
            _fail('THMZ-E2000', '{}: unsupported node field(s) {}'.format(
                context, ', '.join(sorted(unknown))))
        record = {
            'index': _int_field(node, 'Index', context),
            'temperature': _float_field(node, 'Temperature', context),
            'x_flux': _float_field(node, 'X-flux', context),
            'y_flux': _float_field(node, 'Y-flux', context),
        }
        if record['index'] in seen:
            _fail('THMZ-E2000', '{}: duplicate node Index {}'.format(
                context, record['index']))
        seen.add(record['index'])
        for tag, key in (('Humidity', 'humidity'),
                         ('WaterContent', 'water_content')):
            text = node.findtext(tag)
            record[key] = (None if text is None
                           else _float_field(node, tag, context))
        nodes.append(record)
    return nodes


def write_mesh_node_results(nodes, results_type='U-factor'):
    """Serialize node results to ``MeshResults`` XML (str).

    Args:
        nodes: Iterable of dicts with integer ``index``, ``temperature``
            (degrees Celsius), ``x_flux``/``y_flux`` (W/m²), and optional
            ``humidity`` (dimensionless relative humidity) and
            ``water_content`` (kg/m³). Moisture fields are omitted when
            absent or None; supplied finite values are not clipped. Index
            accepts whole numbers and integer text without loss, but not
            booleans, missing/non-finite values or fractions.
        results_type: Result case label, defaulting to ``U-factor``.

    Returns:
        XML text with the node field order used by the data-layer serializer.

    Raises:
        ContractError: ``THMZ-E2000`` for invalid indices or non-finite values.
    """
    context = 'SteadyStateMeshResults.xml'
    root = ET.Element('MeshResults')
    _serialize(root, 'Version', '1')
    case = ET.SubElement(root, 'Case')
    _serialize(case, 'ResultsType', results_type)
    container = ET.SubElement(case, 'Nodes')
    for record in nodes:
        node = ET.SubElement(container, 'Node')
        _serialize(node, 'Index', str(_int_value(
            record['index'], 'Case/Nodes/Node/Index', context)))
        for key, tag in (('temperature', 'Temperature'),
                         ('x_flux', 'X-flux'), ('y_flux', 'Y-flux')):
            value = record[key]
            if not math.isfinite(value):
                _fail('THMZ-E2000', '{}: node {} {} is not finite'.format(
                    context, record['index'], tag))
            _serialize(node, tag, _num(value))
        for key, tag in (('humidity', 'Humidity'),
                         ('water_content', 'WaterContent')):
            value = record.get(key)
            if value is not None:
                if not math.isfinite(value):
                    _fail('THMZ-E2000', '{}: node {} {} is not finite'
                          .format(context, record['index'], tag))
                _serialize(node, tag, _num(value))
    return _XML_DECLARATION + ET.tostring(root, encoding='unicode')
