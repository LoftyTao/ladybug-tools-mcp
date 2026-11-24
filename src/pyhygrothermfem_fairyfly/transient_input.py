"""Transient THMZ input members: TransientTypeBC.xml and timestep files.

Pure-Python reader/writer for the two transient boundary-condition members
mirrored from THERM 8.
Upstream LibraryFEMTherm ships only readers; the writers here are new and
emit the same canonical field order the C++ serializers produce.

No pylibraryfemtherm dependency: ElementTree plus the contract rules. All
contract violations raise the ``errors.make_error`` family (``ContractError``
subclasses that remain ``ValueError``) carrying ``THMZ-Exxxx`` codes.

Schema notes confirmed against the official THERM 8.1 sample input
``Stucco Wall - Moisture.thmz`` (8.0.7.0) and solved exports:
- ``Version`` is tolerated when absent (upstream C++ treats it as optional
  on both members; the sample ``TransientTypeBC.xml`` omits it); a present
  element must spell ``1``. Writers always emit ``Version 1``.
- ``TimestepFileName`` values are treated as bare file names under the fixed
  ``timestep input files`` directory; a spelled-out prefix is also accepted.
- ``bcType=SteadyState`` records carry their constant values on the record;
  their ``Boundary/TransientData/TimestepFileName`` may be empty or omitted
  (the fairyfly-next-therm writer emits an empty element), while
  ``bcType=Transient`` references require a resolvable timestep member.
"""
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
import math
import operator
import xml.etree.ElementTree as ET

from .errors import make_error

TRANSIENT_TYPE_BC_MEMBER = 'TransientTypeBC.xml'
TIMESTEP_DIR = 'timestep input files'

BC_TYPES = ('Transient', 'SteadyState')
BC_MODELS = ('Neumann', 'Dirichlet')
CONVECTION_MODELS = (
    'ASHRAE/NFRC Inside', 'ASHRAE/NFRC Outside', 'Fixed Convection Coefficient',
    'TARP', 'Yazdanian Klems', 'Kimura', 'Montazeri')
RADIATION_MODELS = (
    'Automatic Enclosure', 'Black Body Radiation', 'Fixed Radiation Coefficient')
WIND_DIRECTIONS = ('Windward', 'Leeward')

_ABSOLUTE_ZERO_C = -273.15

# Timestep record layout: XML element name -> ordered value field names.
# Field names are the Pythonic contract names; _TIMESTEP_TAGS maps them onto
# the THERM 8 element spellings.
_CONVECTION_SERIES = {
    'TARPTimestep': ('temperature', 'humidity'),
    'ASHRAETimestepInside': ('temperature', 'humidity'),
    'ASHRAETimestepOutside': ('temperature', 'humidity', 'wind_speed'),
    # The upstream serializer writes FilmCoefficient before Temperature.
    'FixedConvectionFilmTimestep': (
        'film_coefficient', 'temperature', 'humidity'),
    'YazdanianKlemsTimestep': (
        'temperature', 'humidity', 'wind_speed', 'wind_direction'),
    'KimuraTimestep': ('temperature', 'humidity', 'wind_speed',
                       'wind_direction'),
    'MontazeriTimestep': ('temperature', 'humidity', 'wind_speed',
                          'wind_direction'),
}
_RADIATION_SERIES = {
    'FixedRadiationCoefficientTimestep': ('temperature', 'hr'),
    'BlackBodyRadiationTimestep': ('temperature', 'emissivity'),
}
# The upstream writer emits ``FixedRadiationTimestep`` (dead code path) while
# the reader and the XSD use the longer spelling; accept both on read.
_RADIATION_ALIASES = {
    'FixedRadiationTimestep': 'FixedRadiationCoefficientTimestep',
}
_SCALAR_SERIES = {
    'HeatFluxTimestep': ('heat_flux',),
    'SolarRadiationTimestep': ('solar_radiation',),
    'TemperatureTimestep': ('temperature',),
    'HumidityTimestep': ('humidity',),
}
_TIMESTEP_TAGS = {
    'index': 'Index', 'temperature': 'Temperature', 'humidity': 'Humidity',
    'film_coefficient': 'FilmCoefficient', 'wind_speed': 'WindSpeed',
    'wind_direction': 'WindDirection', 'hr': 'hr', 'emissivity': 'Emissivity',
    'heat_flux': 'HeatFlux', 'solar_radiation': 'SolarRadiation',
}

# Convection model -> timestep element that drives it in transient runs.
CONVECTION_TIMESTEP_TAG = {
    'TARP': 'TARPTimestep',
    'ASHRAE/NFRC Inside': 'ASHRAETimestepInside',
    'ASHRAE/NFRC Outside': 'ASHRAETimestepOutside',
    'Fixed Convection Coefficient': 'FixedConvectionFilmTimestep',
    'Yazdanian Klems': 'YazdanianKlemsTimestep',
    'Kimura': 'KimuraTimestep',
    'Montazeri': 'MontazeriTimestep',
}
RADIATION_TIMESTEP_TAG = {
    'Fixed Radiation Coefficient': 'FixedRadiationCoefficientTimestep',
    'Black Body Radiation': 'BlackBodyRadiationTimestep',
    # Upstream has no Automatic-Enclosure timestep record; THERM 8 transient
    # archives pair it with BlackBodyRadiationTimestep (unverified).
    'Automatic Enclosure': 'BlackBodyRadiationTimestep',
}

_XML_DECLARATION = '<?xml version="1.0" encoding="utf-8"?>\n'
_SCHEMA_LOCATION = (
    '{http://www.w3.org/2001/XMLSchema-instance}noNamespaceSchemaLocation')


def _fail(code, message):
    raise make_error(code, message)


def _parse_xml(content, member):
    if isinstance(content, str):
        content = content.encode('utf-8')
    if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
        _fail('THMZ-E1005', '{}: XML entities are not supported'.format(member))
    try:
        return ET.fromstring(content)
    except ET.ParseError as error:
        _fail('THMZ-E1007', '{}: {}'.format(member, error))


def _text(element, tag):
    child = element.find(tag)
    if child is None:
        return None
    _only_fields(child, (), '{} {}'.format(element.tag, tag))
    return (child.text or '').strip()


def _no_duplicate_tags(element, context, repeatable=()):
    tags = Counter(child.tag for child in element)
    duplicated = sorted(tag for tag, count in tags.items()
                        if count > 1 and tag not in repeatable)
    if duplicated:
        _fail('THMZ-E2002', '{}: duplicate field(s) {}'.format(
            context, ', '.join('{} ({} copies)'.format(tag, tags[tag])
                               for tag in duplicated)))


def _only_fields(element, allowed, context, attributes=()):
    unknown = sorted({child.tag for child in element} - set(allowed))
    if unknown:
        _fail('THMZ-E2001', '{}: unsupported field(s) {}'.format(
            context, ', '.join(unknown)))
    unknown_attributes = sorted(set(element.attrib) - set(attributes))
    if unknown_attributes:
        _fail('THMZ-E2001', '{}: unsupported attribute(s) {!r}'.format(
            context, unknown_attributes))


def _required(element, tag, context):
    value = _text(element, tag)
    if not value:
        _fail('THMZ-E2003', '{}: missing or empty {} {!r}'.format(
            context, tag, value))
    return value


def _version(element, context):
    """Read the root ``Version`` element, defaulting a genuine absence to 1.

    The XSDs mark ``Version`` required, but the upstream C++ readers either
    skip it (``BCTransient/Types.cxx`` never reads it) or treat it as an
    optional scalar (``BCTransient/Timestep.cxx``); the THERM 8.1 sample
    input ships a ``TransientTypeBC.xml`` without the element. A *present*
    element must still spell ``1`` -- empty or unrecognized values stay
    contract violations so unknown versions cannot pass silently.
    """
    value = _text(element, 'Version')
    if value is None:
        return '1'
    if value != '1':
        _fail('THMZ-E2000', '{}: unsupported Version {!r}'.format(
            context, value))
    return value


def _bool(element, tag, context):
    value = _required(element, tag, context)
    if value.lower() not in ('true', 'false'):
        _fail('THMZ-E2005', '{}: {} {!r} must be true or false'.format(
            context, tag, value))
    return value.lower() == 'true'


def _number(element, tag, context, required=True):
    text = _text(element, tag)
    if text is None:
        if required:
            _fail('THMZ-E2003', '{}: missing {} {!r}'.format(
                context, tag, text))
        return None
    try:
        value = float(text)
    except ValueError:
        _fail('THMZ-E2004', '{}: {} {!r} must be a finite number'.format(
            context, tag, text))
    if not math.isfinite(value):
        _fail('THMZ-E2004', '{}: {} {!r} must be a finite number'.format(
            context, tag, text))
    return value


def _fraction(value, context):
    if not 0 <= value <= 1:
        _fail('THMZ-E2004', '{} {!r} must be between zero and one'.format(
            context, value))
    return value


def _temperature(value, context):
    if value < _ABSOLUTE_ZERO_C:
        _fail('THMZ-E2004', '{} {!r} is below absolute zero'.format(
            context, value))
    return value


def _num(value):
    return str(int(value)) if float(value).is_integer() else repr(
        float(value))


def _serialize(parent, tag, value):
    if not isinstance(value, str):
        _fail('THMZ-E2004', '{}: {} {!r} must be text'.format(
            parent.tag, tag, value))
    child = ET.SubElement(parent, tag)
    child.text = value
    return child


def _serialize_number(parent, tag, value):
    try:
        finite = not isinstance(value, bool) and math.isfinite(float(value))
        text = _num(value) if finite else None
    except (TypeError, ValueError, OverflowError):
        text = None
    if text is None:
        _fail('THMZ-E2004', '{}: {} {!r} must be a finite number'.format(
            parent.tag, tag, value))
    return _serialize(parent, tag, text)


def _serialize_index(parent, value, context):
    try:
        index = operator.index(value) if not isinstance(value, bool) else 0
    except TypeError:
        index = 0
    if index < 1:
        _fail('THMZ-E2004', '{}: Index {!r} must be a positive integer'
              .format(context, value))
    return _serialize(parent, 'Index', str(index))


def _mapping_fields(values, allowed, context, required=()):
    if not isinstance(values, Mapping):
        _fail('THMZ-E2004', '{}: {!r} must be a field mapping'.format(
            context, values))
    unknown = sorted(set(values) - set(allowed), key=repr)
    if unknown:
        _fail('THMZ-E2001', '{}: unsupported field(s) {!r}'.format(
            context, unknown))
    missing = sorted(set(required) - set(values))
    if missing:
        _fail('THMZ-E2003', '{}: missing field(s) {!r}'.format(
            context, missing))


def _serialize_bool(parent, tag, record, key, context):
    value = record[key]
    if not isinstance(value, bool):
        _fail('THMZ-E2005', '{}: {} {!r} must be a Boolean'.format(
            context, key, value))
    return _serialize(parent, tag, 'true' if value else 'false')


# --- TransientTypeBC.xml -----------------------------------------------------

# Record dict keys mirror the XML schema with Pythonic names:
#   uuid, name, protected, bc_type, bc_model, color,
#   convection/radiation/solar: None or dicts of optional value fields,
#   use_heat_flux/heat_flux, use_temperature/temperature,
#   use_humidity/humidity, project_name (optional).
_CONVECTION_FIELDS = (
    ('model', 'Model'), ('temperature', 'Temperature'),
    ('film_coefficient', 'FilmCoefficient'), ('wind_speed', 'WindSpeed'),
    ('wind_direction', 'WindDirection'))
_RADIATION_FIELDS = (
    ('model', 'Model'), ('temperature', 'Temperature'),
    ('surface_emissivity', 'SurfaceEmissivity'),
    ('view_factor', 'ViewFactor'), ('hr', 'hr'))
_SOLAR_FIELDS = (
    ('solar_radiation', 'SolarRadiation'), ('absorptance', 'Absorptance'))
_RECORD_TAGS = (
    'UUID', 'Name', 'ProjectName', 'Protected', 'bcType', 'bcModel',
    'Convection', 'Radiation', 'Solar', 'UseHeatFlux', 'HeatFlux',
    'UseTemperature', 'Temperature', 'UseHumidity', 'Humidity', 'Color')


def _read_enum(element, tag, values, context):
    value = _required(element, tag, context)
    if value not in values:
        _fail('THMZ-E2005', '{}: illegal {} {!r}'.format(context, tag, value))
    return value


def _read_sub_record(element, fields, context):
    record = {}
    _no_duplicate_tags(element, context)
    _only_fields(element, {tag for _, tag in fields}, context)
    for key, tag in fields:
        text = _text(element, tag)
        if text is None:
            continue
        if key in ('model', 'wind_direction'):
            record[key] = text
        else:
            record[key] = _number(element, tag, context)
    return record


def _read_type_record(element, index):
    context = 'TransientTypeBC.xml record {}'.format(index)
    _no_duplicate_tags(element, context)
    _only_fields(element, _RECORD_TAGS, context)
    record = {
        'uuid': _required(element, 'UUID', context),
        'name': _required(element, 'Name', context),
        'protected': _bool(element, 'Protected', context),
        'bc_type': _read_enum(element, 'bcType', BC_TYPES, context),
        'bc_model': _read_enum(element, 'bcModel', BC_MODELS, context),
        'use_heat_flux': _bool(element, 'UseHeatFlux', context),
        'use_temperature': _bool(element, 'UseTemperature', context),
        'use_humidity': _bool(element, 'UseHumidity', context),
        'color': _required(element, 'Color', context),
        'convection': None, 'radiation': None, 'solar': None,
        'heat_flux': None, 'temperature': None, 'humidity': None,
    }
    project_name = _text(element, 'ProjectName')
    if project_name is not None:
        record['project_name'] = project_name
    convection = element.find('Convection')
    if convection is not None:
        sub = _read_sub_record(convection, _CONVECTION_FIELDS,
                               context + ' Convection')
        if 'model' not in sub or sub['model'] not in CONVECTION_MODELS:
            _fail('THMZ-E2005', '{}: illegal Convection Model {!r}'.format(
                context, sub.get('model')))
        if 'wind_direction' in sub and \
                sub['wind_direction'] not in WIND_DIRECTIONS:
            _fail('THMZ-E2005', '{}: illegal WindDirection {!r}'.format(
                context, sub['wind_direction']))
        if 'temperature' in sub:
            _temperature(sub['temperature'],
                         context + ' Convection Temperature')
        record['convection'] = sub
    radiation = element.find('Radiation')
    if radiation is not None:
        sub = _read_sub_record(radiation, _RADIATION_FIELDS,
                               context + ' Radiation')
        if 'model' not in sub or sub['model'] not in RADIATION_MODELS:
            _fail('THMZ-E2005', '{}: illegal Radiation Model {!r}'.format(
                context, sub.get('model')))
        for key in ('surface_emissivity', 'view_factor'):
            if key in sub:
                _fraction(sub[key], context + ' Radiation ' + key)
        if 'temperature' in sub:
            _temperature(sub['temperature'], context + ' Radiation Temperature')
        record['radiation'] = sub
    solar = element.find('Solar')
    if solar is not None:
        sub = _read_sub_record(solar, _SOLAR_FIELDS, context + ' Solar')
        if 'absorptance' in sub:
            _fraction(sub['absorptance'], context + ' Solar Absorptance')
        record['solar'] = sub
    for use_key, value_key in (('use_heat_flux', 'heat_flux'),
                               ('use_temperature', 'temperature'),
                               ('use_humidity', 'humidity')):
        tag = {'heat_flux': 'HeatFlux', 'temperature': 'Temperature',
               'humidity': 'Humidity'}[value_key]
        value = _number(element, tag, context, required=False)
        if value is not None:
            if value_key == 'humidity':
                _fraction(value, context + ' Humidity')
            if value_key == 'temperature':
                _temperature(value, context + ' Temperature')
            record[value_key] = value
    return record


def load_transient_type_bc(content):
    """Parse TransientTypeBC.xml into a list of record dicts.

    Args:
        content: XML bytes or string of the TransientTypeBC.xml member.

    Returns:
        List of record dicts keyed by the Pythonic names documented at
        ``_RECORD_TAGS`` (``uuid``, ``name``, ``bc_type``, ``bc_model``,
        ``convection``/``radiation``/``solar`` sub-record dicts or None,
        ``use_heat_flux``/``heat_flux``, ``use_temperature``/``temperature``,
        ``use_humidity``/``humidity``, ``color`` and optional
        ``project_name``).

    Raises:
        ValueError: Contract violation; message starts with a THMZ-E code.
    """
    root = _parse_xml(content, TRANSIENT_TYPE_BC_MEMBER)
    context = TRANSIENT_TYPE_BC_MEMBER
    if root.tag != 'BoundaryConditionsType':
        _fail('THMZ-E2000', '{}: expected BoundaryConditionsType root'.format(
            context))
    _only_fields(root, {'Version', 'BoundaryConditionType'}, context)
    _no_duplicate_tags(root, context, repeatable=('BoundaryConditionType',))
    _version(root, context)
    records = [_read_type_record(element, index + 1)
               for index, element in enumerate(
                   root.findall('BoundaryConditionType'))]
    uuids = Counter(record['uuid'] for record in records)
    names = Counter(record['name'] for record in records)
    for tag, counts in (('UUID', uuids), ('Name', names)):
        duplicated = sorted(value for value, count in counts.items()
                            if count > 1)
        if duplicated:
            _fail('THMZ-E2002', '{}: duplicate record {} {!r}'.format(
                context, tag, duplicated))
    return records


def _write_sub_record(parent, tag, values, fields):
    _mapping_fields(values, {key for key, _ in fields}, parent.tag + ' ' + tag)
    element = ET.SubElement(parent, tag)
    for key, child_tag in fields:
        value = values.get(key)
        if value is None:
            continue
        if key in ('model', 'wind_direction'):
            _serialize(element, child_tag, value)
        else:
            _serialize_number(element, child_tag, value)
    return element


def save_transient_type_bc(records):
    """Serialize record dicts to TransientTypeBC.xml content (str).

    Field order mirrors the THERM 8 sample file: Color last, even though the
    XSD sequence lists it earlier (matching the C++ serializer, not the XSD).

    Args:
        records: List of record dicts in the shape returned by
            :func:`load_transient_type_bc`.

    Returns:
        TransientTypeBC.xml member content as a Unicode string including
        the XML declaration.

    Raises:
        ValueError: Invalid or unsupported fields carry the corresponding
            THMZ-E code. Unrepresentable values are never omitted.
    """
    root = ET.Element('BoundaryConditionsType')
    _serialize(root, 'Version', '1')
    for index, record in enumerate(records):
        context = 'TransientTypeBC.xml record {}'.format(index + 1)
        required = {'uuid', 'name', 'protected', 'bc_type', 'bc_model',
                    'use_heat_flux', 'use_temperature', 'use_humidity', 'color'}
        allowed = required | {'project_name', 'convection', 'radiation',
                              'solar', 'heat_flux', 'temperature', 'humidity'}
        _mapping_fields(record, allowed, context, required=required)
        element = ET.SubElement(root, 'BoundaryConditionType')
        _serialize(element, 'UUID', record['uuid'])
        _serialize(element, 'Name', record['name'])
        if record.get('project_name') is not None:
            _serialize(element, 'ProjectName', record['project_name'])
        _serialize_bool(element, 'Protected', record, 'protected', context)
        if record['bc_type'] not in BC_TYPES:
            _fail('THMZ-E2005', '{}: illegal bcType {!r}'.format(
                context, record['bc_type']))
        if record['bc_model'] not in BC_MODELS:
            _fail('THMZ-E2005', '{}: illegal bcModel {!r}'.format(
                context, record['bc_model']))
        _serialize(element, 'bcType', record['bc_type'])
        _serialize(element, 'bcModel', record['bc_model'])
        if record.get('convection') is not None:
            _mapping_fields(record['convection'],
                            {key for key, _ in _CONVECTION_FIELDS},
                            context + ' Convection')
            model = record['convection'].get('model')
            if model not in CONVECTION_MODELS:
                _fail('THMZ-E2005', '{}: illegal Convection Model {!r}'.format(
                    context, model))
            _write_sub_record(element, 'Convection', record['convection'],
                              _CONVECTION_FIELDS)
        if record.get('radiation') is not None:
            _mapping_fields(record['radiation'],
                            {key for key, _ in _RADIATION_FIELDS},
                            context + ' Radiation')
            model = record['radiation'].get('model')
            if model not in RADIATION_MODELS:
                _fail('THMZ-E2005', '{}: illegal Radiation Model {!r}'.format(
                    context, model))
            _write_sub_record(element, 'Radiation', record['radiation'],
                              _RADIATION_FIELDS)
        if record.get('solar') is not None:
            _write_sub_record(element, 'Solar', record['solar'],
                              _SOLAR_FIELDS)
        _serialize_bool(element, 'UseHeatFlux', record, 'use_heat_flux', context)
        if record.get('heat_flux') is not None:
            _serialize_number(element, 'HeatFlux', record['heat_flux'])
        _serialize_bool(element, 'UseTemperature', record,
                        'use_temperature', context)
        if record.get('temperature') is not None:
            _serialize_number(element, 'Temperature', record['temperature'])
        _serialize_bool(element, 'UseHumidity', record, 'use_humidity', context)
        if record.get('humidity') is not None:
            _serialize_number(element, 'Humidity', record['humidity'])
        _serialize(element, 'Color', record['color'])
    content = _XML_DECLARATION + ET.tostring(root, encoding='unicode')
    load_transient_type_bc(content)
    return content


# --- timestep input files ----------------------------------------------------

@dataclass
class TimestepFile:
    """Contents of one ``timestep input files/<name>.xml`` member.

    ``convection`` and ``radiation`` map timestep element names to tuples of
    entry dicts; the scalar series are flat tuples of entry dicts. Entry
    dicts use the Pythonic field names of ``_TIMESTEP_TAGS`` and may carry an
    optional ``index`` (1-based timestep number; THERM files frequently omit
    it or restart numbering).

    Properties:
        name: ``Name`` element of the timestep file (the boundary record
            name it belongs to).
        index: Optional 1-based ``BoundaryConditionTransient/Index`` label;
            THERM writes it on some exports. None when absent.
        convection: Dict mapping a convection timestep element name (e.g.
            ``FixedConvectionFilmTimestep``) to a tuple of entry dicts with
            temperature in degC, relative humidity in [0, 1], film coefficient
            in W/(m2 K), and wind speed in m/s. ``wind_direction`` retains the
            upstream numeric value; its angular unit is unverified.
        radiation: Dict mapping a radiation timestep element name
            (``FixedRadiationCoefficientTimestep``,
            ``BlackBodyRadiationTimestep``) to entry tuples with
            temperature in degC plus ``hr`` in W/(m2 K) or dimensionless
            emissivity in [0, 1].
        heat_flux: Tuple of ``HeatFluxTimestep`` entry dicts
            (``heat_flux``, W/m2).
        solar_radiation: Tuple of ``SolarRadiationTimestep`` entry dicts
            (``solar_radiation``, W/m2).
        temperature: Tuple of ``TemperatureTimestep`` entry dicts
            (``temperature``, degC).
        humidity: Tuple of ``HumidityTimestep`` entry dicts
            (``humidity``, relative humidity in [0, 1]).
        schema_location: Optional XML schema-location hint from the official
            input. Preserved on write; None when the root has no hint.
    """
    name: str
    index: int = None
    convection: dict = field(default_factory=dict)
    radiation: dict = field(default_factory=dict)
    heat_flux: tuple = ()
    solar_radiation: tuple = ()
    temperature: tuple = ()
    humidity: tuple = ()
    schema_location: str = None

    def __post_init__(self):
        self.convection = {tag: tuple(entries)
                           for tag, entries in self.convection.items()}
        self.radiation = {tag: tuple(entries)
                          for tag, entries in self.radiation.items()}
        self.heat_flux = tuple(self.heat_flux)
        self.solar_radiation = tuple(self.solar_radiation)
        self.temperature = tuple(self.temperature)
        self.humidity = tuple(self.humidity)


def _read_timestep_entry(element, fields, context):
    _no_duplicate_tags(element, context)
    _only_fields(element, {'Index'} | {_TIMESTEP_TAGS[key] for key in fields},
                 context)
    entry = {'index': None}
    index = _text(element, 'Index')
    if index is not None:
        try:
            entry['index'] = int(index)
        except ValueError:
            _fail('THMZ-E2004', '{}: Index {!r} must be an integer'.format(
                context, index))
        if entry['index'] < 1:
            _fail('THMZ-E2004', '{}: Index {!r} must be >= 1'.format(
                context, index))
    for key in fields:
        value = _number(element, _TIMESTEP_TAGS[key], context)
        if key == 'humidity':
            _fraction(value, context + ' Humidity')
        elif key == 'temperature':
            _temperature(value, context + ' Temperature')
        elif key == 'emissivity':
            _fraction(value, context + ' Emissivity')
        entry[key] = value
    return entry


def load_timestep_file(content, member='timestep input files'):
    """Parse one timestep file into a :class:`TimestepFile`.

    Args:
        content: XML bytes or string.
        member: Archive member name used in error context.

    Returns:
        A :class:`TimestepFile` with the parsed timestep series.

    Raises:
        ValueError: Contract violation; message starts with a THMZ-E code.
    """
    context = member
    root = _parse_xml(content, member)
    if root.tag != 'InputBoundaryConditionsData':
        _fail('THMZ-E2000', '{}: expected InputBoundaryConditionsData root'
              .format(context))
    _only_fields(root, {'Version', 'Name', 'BoundaryConditionTransient'},
                 context, attributes=(_SCHEMA_LOCATION,))
    _no_duplicate_tags(root, context)
    _version(root, context)
    result = TimestepFile(name=_required(root, 'Name', context),
                          schema_location=root.get(_SCHEMA_LOCATION))
    transient = root.find('BoundaryConditionTransient')
    if transient is None:
        return result
    _only_fields(
        transient,
        {'Index', 'ConvectionTimesteps', 'RadiationTimesteps'} |
        set(_SCALAR_SERIES), context)
    _no_duplicate_tags(transient, context, repeatable=_SCALAR_SERIES)
    index = _text(transient, 'Index')
    if index is not None:
        try:
            result.index = int(index)
        except ValueError:
            _fail('THMZ-E2004', '{}: Index {!r} must be an integer'.format(
                context, index))
        if result.index < 1:
            _fail('THMZ-E2004', '{}: Index {!r} must be >= 1'.format(
                context, index))
    convection = transient.find('ConvectionTimesteps')
    if convection is not None:
        _only_fields(convection, set(_CONVECTION_SERIES), context)
        for element in convection:
            tag = element.tag
            entry = _read_timestep_entry(
                element, _CONVECTION_SERIES[tag], context + ' ' + tag)
            result.convection.setdefault(tag, []).append(entry)
    radiation = transient.find('RadiationTimesteps')
    if radiation is not None:
        allowed = set(_RADIATION_SERIES) | set(_RADIATION_ALIASES)
        _only_fields(radiation, allowed, context)
        for element in radiation:
            tag = _RADIATION_ALIASES.get(element.tag, element.tag)
            entry = _read_timestep_entry(
                element, _RADIATION_SERIES[tag], context + ' ' + tag)
            result.radiation.setdefault(tag, []).append(entry)
    scalar_targets = {'HeatFluxTimestep': 'heat_flux',
                      'SolarRadiationTimestep': 'solar_radiation',
                      'TemperatureTimestep': 'temperature',
                      'HumidityTimestep': 'humidity'}
    for tag, fields in _SCALAR_SERIES.items():
        target = scalar_targets[tag]
        entries = list(getattr(result, target))
        for element in transient.findall(tag):
            entries.append(_read_timestep_entry(
                element, fields, context + ' ' + tag))
        setattr(result, target, entries)
    result.__post_init__()
    return result


def _write_timestep_entry(parent, tag, entry, fields, context):
    _mapping_fields(entry, {'index'} | set(fields), context, required=fields)
    element = ET.SubElement(parent, tag)
    index = entry.get('index')
    if index is not None:
        _serialize_index(element, index, context)
    for key in fields:
        _serialize_number(element, _TIMESTEP_TAGS[key], entry[key])


def save_timestep_file(timestep_file):
    """Serialize a :class:`TimestepFile` to XML (str).

    Field order mirrors the upstream C++ serializers (e.g.
    FixedConvectionFilmTimestep writes FilmCoefficient before Temperature).

    Args:
        timestep_file: The :class:`TimestepFile` to serialize.

    Returns:
        Timestep member content as a Unicode string including the XML
        declaration.

    Raises:
        ValueError: Invalid or unsupported fields carry the corresponding
            THMZ-E code. Unrepresentable values are never omitted.
    """
    root = ET.Element('InputBoundaryConditionsData')
    if timestep_file.schema_location is not None:
        if not isinstance(timestep_file.schema_location, str):
            _fail('THMZ-E2004', 'timestep file: schema_location {!r} '
                  'must be text'.format(timestep_file.schema_location))
        root.set(_SCHEMA_LOCATION, timestep_file.schema_location)
    _mapping_fields(timestep_file.convection, _CONVECTION_SERIES,
                    'timestep file ConvectionTimesteps')
    _mapping_fields(timestep_file.radiation, _RADIATION_SERIES,
                    'timestep file RadiationTimesteps')
    _serialize(root, 'Version', '1')
    _serialize(root, 'Name', timestep_file.name)
    transient = ET.SubElement(root, 'BoundaryConditionTransient')
    if timestep_file.index is not None:
        _serialize_index(transient, timestep_file.index, 'timestep file')
    if any(timestep_file.convection.values()):
        container = ET.SubElement(transient, 'ConvectionTimesteps')
        for tag, fields in _CONVECTION_SERIES.items():
            for entry in timestep_file.convection.get(tag, ()):
                _write_timestep_entry(
                    container, tag, entry, fields,
                    'timestep file ' + tag)
    if any(timestep_file.radiation.values()):
        container = ET.SubElement(transient, 'RadiationTimesteps')
        for tag, fields in _RADIATION_SERIES.items():
            for entry in timestep_file.radiation.get(tag, ()):
                _write_timestep_entry(
                    container, tag, entry, fields,
                    'timestep file ' + tag)
    for tag, key in (('HeatFluxTimestep', 'heat_flux'),
                     ('SolarRadiationTimestep', 'solar_radiation'),
                     ('TemperatureTimestep', 'temperature'),
                     ('HumidityTimestep', 'humidity')):
        for entry in getattr(timestep_file, key):
            _write_timestep_entry(
                transient, tag, entry, _SCALAR_SERIES[tag],
                'timestep file ' + tag)
    content = _XML_DECLARATION + ET.tostring(root, encoding='unicode')
    load_timestep_file(content)
    return content


def transient_timestep_member(file_name):
    """Archive member name for a timestep file name.

    Args:
        file_name: Bare file name written in
            ``Boundary/TransientData/TimestepFileName``.

    Returns:
        The archive member name ``timestep input files/<file_name>``.
    """
    return TIMESTEP_DIR + '/' + file_name


def _timestep_member_name(file_name):
    """Normalize a TimestepFileName value to an archive member name."""
    name = file_name.replace('\\', '/').strip()
    if name.startswith(TIMESTEP_DIR + '/'):
        name = name[len(TIMESTEP_DIR) + 1:]
    if not name or '/' in name or name in ('.', '..'):
        _fail('THMZ-E2000', 'TimestepFileName {!r} must be a bare file name '
              'under {!r}'.format(file_name, TIMESTEP_DIR))
    return transient_timestep_member(name)


def _require_timestep_series(tag, series, context):
    if not series.get(tag):
        _fail('THMZ-E4000', '{}: timestep file has no {} records'.format(
            context, tag))


def validate_transient_inputs(members):
    """Cross-validate transient members against Model.xml.

    Args:
        members: Mapping of archive member name to bytes (or str).

    Returns:
        List of dicts, one per ``Boundary/TransientData`` reference, with
        ``boundary_id``, ``boundary_name``, ``record`` (the resolved
        TransientTypeBC record dict), ``timestep_member`` and
        ``timestep_file`` (the parsed :class:`TimestepFile`); the last two
        are None when a ``bcType=SteadyState`` record leaves
        ``TimestepFileName`` empty or absent.

    Raises:
        ValueError: Contract violations carry THMZ-E codes. Missing required
            members raise THMZ-E1004, the Montazeri convection model raises
            THMZ-E5001, and unreferenced timestep members raise THMZ-E5013.
    """
    model_content = members.get('Model.xml')
    if model_content is None:
        _fail('THMZ-E1004', 'Model.xml is required for transient validation')
    model = _parse_xml(model_content, 'Model.xml')
    type_content = members.get(TRANSIENT_TYPE_BC_MEMBER)
    if type_content is None:
        _fail('THMZ-E1004', '{} is required for transient validation'.format(
            TRANSIENT_TYPE_BC_MEMBER))
    records = load_transient_type_bc(type_content)
    records_by_uuid = {record['uuid']: record for record in records}

    references = []
    timestep_members = set()
    for boundary in model.findall('Boundaries/Boundary'):
        if len(boundary.findall('TransientData')) > 1:
            _fail('THMZ-E2002', 'Boundary {}: duplicate TransientData '
                  '({} copies)'.format(boundary.findtext('ID') or '?',
                                       len(boundary.findall('TransientData'))))
        transient_data = boundary.find('TransientData')
        if transient_data is None:
            continue
        boundary_id = boundary.findtext('ID') or '?'
        context = 'Boundary {} TransientData'.format(boundary_id)
        _no_duplicate_tags(transient_data, context)
        _only_fields(transient_data,
                     {'UUID', 'TimestepFileName', 'Surface', 'Building'},
                     context)
        uuid = _required(transient_data, 'UUID', context)
        if uuid not in records_by_uuid:
            _fail('THMZ-E4000', '{}: UUID {!r} resolves to no '
                  'TransientTypeBC record'.format(context, uuid))
        record = records_by_uuid[uuid]
        for optional, fields in (
                ('Surface', {'Tilt', 'Length'}),
                ('Building', {'Width', 'Height'})):
            block = transient_data.find(optional)
            if block is not None:
                _no_duplicate_tags(block, context + ' ' + optional)
                _only_fields(block, fields, context + ' ' + optional)
                for tag in fields:
                    if _text(block, tag) is not None:
                        _number(block, tag, context + ' ' + optional)
        # bcType=SteadyState records are driven by their constant fields;
        # THERM 8 and the Fairyfly-Next writer leave TimestepFileName empty
        # (or omitted) on them, so no timestep member is required.
        file_name = _text(transient_data, 'TimestepFileName')
        member = None
        timestep_file = None
        if not file_name:
            if record['bc_type'] != 'SteadyState':
                _fail('THMZ-E2000', '{}: TimestepFileName is required for '
                      'Transient records'.format(context))
        else:
            member = _timestep_member_name(file_name)
            if member not in members:
                _fail('THMZ-E1004', '{}: missing timestep member {}'.format(
                    context, member))
            timestep_members.add(member)
            timestep_file = load_timestep_file(
                members[member], member=member)
        references.append({
            'boundary_id': boundary_id,
            'boundary_name': boundary.findtext('Name'),
            'record': record,
            'timestep_member': member,
            'timestep_file': timestep_file,
        })

    for name in members:
        if name.startswith(TIMESTEP_DIR + '/') and name not in timestep_members:
            _fail('THMZ-E5013', '{} is not referenced by any boundary '
                  'TransientData'.format(name))

    for reference in references:
        record = reference['record']
        timestep_file = reference['timestep_file']
        context = 'Boundary {}'.format(reference['boundary_id'])
        # The Montazeri rejection is model-level: it applies to every
        # record whatever its bcType and whatever else it declares,
        # including bcType=SteadyState records (whose constant fields are
        # the ones that drive the boundary) and humidity-pinned records
        # (whose convection declaration is inert metadata). It must not be
        # skipped by the series-level early exits below.
        convection = record.get('convection')
        if convection is not None and convection['model'] == 'Montazeri':
            _fail('THMZ-E5001', '{}: Montazeri convection model has no '
                  'kernel implementation'.format(context))
        if timestep_file is not None and \
                'MontazeriTimestep' in timestep_file.convection:
            _fail('THMZ-E5001', '{}: Montazeri timesteps have no kernel '
                  'implementation'.format(context))
        if record['bc_type'] != 'Transient':
            # SteadyState records are driven by constant fields; any named
            # timestep member was already structure-checked on load and its
            # series are not consulted.
            continue
        # Pins dominate every other declaration on the record: a
        # UseHumidity boundary that pins (UseTemperature as well, or any
        # Dirichlet-model record) owns the edge completely, so convection,
        # radiation, heat flux and solar declarations are inert metadata
        # and no timestep series are required for them (contract section
        # 5). The model-level Montazeri check above still applies.
        pinned = (record['use_humidity'] and
                  (record['use_temperature'] or
                   record['bc_model'] == 'Dirichlet'))
        if convection is not None:
            tag = CONVECTION_TIMESTEP_TAG.get(convection['model'])
            if tag is not None and not pinned:
                _require_timestep_series(
                    tag, timestep_file.convection, context)
        if record.get('radiation') and not pinned:
            tag = RADIATION_TIMESTEP_TAG.get(record['radiation']['model'])
            if tag is not None and not timestep_file.radiation.get(tag) \
                    and 'Automatic Enclosure' != record['radiation']['model']:
                _fail('THMZ-E4000', '{}: timestep file has no {} records'
                      .format(context, tag))
        if record['use_heat_flux'] and not pinned:
            if not timestep_file.heat_flux:
                _fail('THMZ-E4000', '{}: timestep file has no HeatFluxTimestep'
                      .format(context))
        if record['use_temperature'] and not timestep_file.temperature:
            _fail('THMZ-E4000', '{}: timestep file has no TemperatureTimestep'
                  .format(context))
        if record['use_humidity'] and not timestep_file.humidity:
            # The HumidityTimestep series is needed when the record pins
            # humidity directly: UseTemperature+UseHumidity (the T+phi pin)
            # or a humidity-only pin on any Dirichlet-style boundary --
            # bcModel routes the BC, so a declared Convection sub-record on
            # a Dirichlet record stays inert and the pin series is still
            # required. A Neumann-style boundary takes the air humidity
            # from the convection timestep series (FixedConvectionFilm-
            # Timestep carries the Humidity column), while Neumann without
            # a Convection model is a solve-layer rejection (E5016), not an
            # input error.
            needs_pin_series = (
                record['use_temperature'] or
                record['bc_model'] == 'Dirichlet')
            if needs_pin_series:
                _fail('THMZ-E4000', '{}: timestep file has no '
                      'HumidityTimestep'.format(context))
        if record.get('solar') is not None and not pinned:
            if not timestep_file.solar_radiation:
                _fail('THMZ-E4000', '{}: timestep file has no '
                      'SolarRadiationTimestep'.format(context))
    return references
