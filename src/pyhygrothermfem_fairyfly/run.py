"""Validated, atomic THMZ execution for thermal and hygrothermal models."""
from collections import Counter, namedtuple
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from io import BytesIO


def _package_version():
    """Return the distribution version for pyHygroThermFEM-Fairyfly or host package."""
    for dist_name in ('pyHygroThermFEM-Fairyfly', 'lbt-mcp'):
        try:
            return version(dist_name)
        except PackageNotFoundError:
            continue
    return '0.1.0+bundled'
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile

import pylibraryfemtherm as fem

from .errors import (ContractError, SolveError, make_error,
                     TRANSIENT_BOUNDARY_WITHOUT_DATA)
from .results import InspectionIssue, InspectionReport, SolvedResult
from ._build_source import verified_kernel_commit

MAX_ARCHIVE_BYTES = 128 * 1024 ** 2
# Mesh.xml coordinates are rounded to 1e-6 m; compare in model millimetres.
BOUNDARY_TOLERANCE_MM = 1e-3
# Match the pinned HygroThermFEM constant (W/m2/K4).
STEFAN_BOLTZMANN = 5.6697e-8
# THMZ contract version implemented here: 2.1 encoded as major * 1000 + minor.
# Minor 2.1 adds the owned-layout HeatFluxStepExchange/WaterFluxStepExchange
# members (ADR-0010 option a); both layouts remain readable.
CONTRACT_VERSION = 2001
# Release sequence written to pyHygroTherm.json for deployment handshakes.
SOLVER_VERSION = 1
# Members whose values are produced by a solve and therefore replaced.
RESULT_MEMBERS = frozenset({
    'SteadyStateResults.xml', 'SteadyStateMeshResults.xml',
    'pyHygroTherm.json'})

# Kernel PhysicsOptions as a named tuple: field order matches the C++
# ``PhysicsOptionsInput`` argument of ``_native.solve_hygrothermal``, so
# instances can cross the binding unchanged while call sites stay
# self-documenting.
_PhysicsOptions = namedtuple('_PhysicsOptions', (
    'exclude_liquid_transport', 'exclude_evaporation_heat',
    'exclude_capillary_conduction', 'exclude_vapor_conduction',
    'exclude_fusion_heat', 'variable_conductivity'))

# Per-element material record passed to the native solvers; field order
# matches the ``MaterialInput`` tuple in steady_solver.hxx. Cavity fields
# are empty/zero for solids (``cavity_standard == ''`` marks a solid).
_MaterialSpec = namedtuple('_MaterialSpec', (
    'conductivity', 'emissivity_front', 'emissivity_back',
    'cavity_standard', 'cavity_gas', 'region_key', 'local_emissivities',
    'cavity_height', 'cavity_pressure'))


def _contract(code, message):
    """Build the ContractError subclass matching the code's range."""
    return make_error(code, message)


def _finite(value, field):
    if value is None or not math.isfinite(value):
        raise _contract('THMZ-E2004', '{} must be a finite number'.format(field))
    return value


def _xml_number(parent, path, field):
    text = parent.findtext(path)
    try:
        value = float(text)
    except (TypeError, ValueError) as error:
        raise _contract('THMZ-E2004', '{} must be a finite number'.format(field)) from error
    return _finite(value, field)


def _only_fields(element, allowed, field):
    unknown = sorted({child.tag for child in element} - set(allowed))
    if unknown:
        raise _contract('THMZ-E2001', '{}: unsupported field(s) {}'.format(
            field, ', '.join(unknown)))


def _fraction(value, field):
    if not 0 <= _finite(value, field) <= 1:
        raise _contract('THMZ-E2005', '{} must be between zero and one'.format(field))
    return value


def _condition_values(condition):
    name = condition.findtext('Name')
    if not name:
        raise _contract('THMZ-E2003', 'SteadyStateBC.xml: boundary condition has no Name')
    for element in condition.iter():
        fields = [child.tag for child in element]
        if len(fields) != len(set(fields)):
            raise _contract('THMZ-E2005', '{}: duplicate {} fields'.format(name, element.tag))
    if condition.find('RadiationSurface') is not None:
        raise _contract('THMZ-E5008', '{}: RadiationSurface conditions are '
                        'unsupported'.format(name))
    _only_fields(condition, {
        'UUID', 'Name', 'ProjectNameTag', 'Protected', 'Color', 'IGUSurface',
        'Simplified', 'Comprehensive'}, 'Boundary condition {}'.format(name))
    igu_surface = condition.findtext('IGUSurface')
    if igu_surface and igu_surface.lower() == 'true':
        raise _contract('THMZ-E5009', '{}: IGU surface boundaries are unsupported'.format(name))

    simple = condition.find('Simplified')
    comprehensive = condition.find('Comprehensive')
    if (simple is None) == (comprehensive is None):
        raise _contract('THMZ-E2002', '{}: expected one steady boundary condition form'.format(name))
    if simple is not None:
        _only_fields(simple, {'Temperature', 'FilmCoefficient', 'RelativeHumidity'},
                     '{} Simplified'.format(name))
        temperature = _xml_number(simple, 'Temperature',
                                  '{} Temperature'.format(name))
        film = _xml_number(simple, 'FilmCoefficient',
                           '{} FilmCoefficient'.format(name))
        humidity = _boundary_humidity(simple, name)
        return film, temperature, 0.0, 0.0, temperature, 1.0, humidity

    _only_fields(comprehensive, {
        'RelativeHumidity', 'Convection', 'ConstantFlux', 'Radiation'},
        '{} Comprehensive'.format(name))
    convection = comprehensive.find('Convection')
    if convection is None:
        raise _contract('THMZ-E2003', '{}: comprehensive convection is missing'.format(name))
    _only_fields(convection, {'Temperature', 'FilmCoefficient'},
                 '{} Convection'.format(name))
    film = _xml_number(convection, 'FilmCoefficient',
                       '{} FilmCoefficient'.format(name))
    temperature = _xml_number(convection, 'Temperature',
                              '{} Temperature'.format(name))

    flux = 0.0
    constant_flux = comprehensive.find('ConstantFlux')
    if constant_flux is not None:
        _only_fields(constant_flux, {'Flux'}, '{} ConstantFlux'.format(name))
        if constant_flux.find('Flux') is not None:
            flux = _xml_number(constant_flux, 'Flux', '{} Flux'.format(name))

    emissivity, radiant_temperature, view_factor = 0.0, temperature, 1.0
    radiation = comprehensive.find('Radiation')
    if radiation is not None:
        for child in radiation:
            if child.tag in ('ManualEnclosure', 'Linear'):
                raise _contract(
                    'THMZ-E5007', '{}: {} Radiation models are unsupported'
                    .format(name, child.tag))
        _only_fields(radiation, {'BlackBodyRadiation', 'AutomaticEnclosure'},
                     '{} Radiation'.format(name))
        if len(radiation) > 1:
            raise _contract('THMZ-E2002', '{}: expected one Radiation model'.format(name))
        for enclosure in radiation:
            _only_fields(enclosure, {'Temperature', 'Emissivity', 'ViewFactor'},
                         '{} Radiation {}'.format(name, enclosure.tag))
            field = '{} Radiation Emissivity'.format(name)
            emissivity = _fraction(_xml_number(enclosure, 'Emissivity', field),
                                   field)
            if enclosure.tag != 'BlackBodyRadiation':
                if emissivity:
                    raise _contract('THMZ-E5007', '{}: active Radiation enclosure is unsupported'
                                     .format(name))
                continue
            radiant_temperature = _xml_number(
                enclosure, 'Temperature', '{} Radiation Temperature'.format(name))
            if radiant_temperature < -273.15:
                raise _contract('THMZ-E2005', '{}: Radiation temperature is below absolute zero'
                                 .format(name))
            field = '{} Radiation ViewFactor'.format(name)
            view_factor = _fraction(_xml_number(enclosure, 'ViewFactor', field),
                                    field)
    humidity = _boundary_humidity(comprehensive, name)
    return (film, temperature, flux, emissivity, radiant_temperature,
            view_factor, humidity)


def _boundary_humidity(condition_block, name):
    """Read the optional ``RelativeHumidity`` of a steady BC record.

    Returns the declared relative humidity fraction, or None when the
    boundary condition makes no humidity statement (treated as a sealed,
    vapor-impermeable surface in hygrothermal solves).
    """
    text = condition_block.findtext('RelativeHumidity')
    if text is None:
        return None
    field = '{} RelativeHumidity'.format(name)
    return _fraction(_xml_number(condition_block, 'RelativeHumidity', field),
                     field)


def _hygro_scalar(hygro, tag, material_uuid):
    """Read a required scalar field of a Solid/HygroThermal record."""
    field = 'Material {} {}'.format(material_uuid, tag)
    text = hygro.findtext(tag)
    if text is None:
        raise _contract('THMZ-E2003', '{} is required for hygrothermal '
                        'solves'.format(field))
    try:
        value = float(text)
    except (TypeError, ValueError) as error:
        raise _contract('THMZ-E2004', '{} must be a finite number; received '
                        '{!r}'.format(field, text)) from error
    if not math.isfinite(value):
        raise _contract('THMZ-E2004', '{} must be a finite number; received '
                        '{!r}'.format(field, text))
    return value


def _hygro_table(hygro, tag, material_uuid):
    """Read a HygroThermal table as a list of finite (x, y) tuples."""
    field = 'Material {} {}'.format(material_uuid, tag)
    element = hygro.find(tag)
    if element is None:
        return None
    if len(element):
        _only_fields(element, {'TableValue'}, field)
    table = []
    for pair in element.findall('TableValue'):
        _only_fields(pair, {'x', 'y'}, field)
        table.append((_xml_number(pair, 'x', field),
                      _xml_number(pair, 'y', field)))
    xs = [pair[0] for pair in table]
    if any(a >= b for a, b in zip(xs, xs[1:])):
        raise _contract('THMZ-E2004', '{}: table x values must be strictly '
                        'increasing'.format(field))
    return table


def _table_value(table, x):
    """Piecewise-linear table lookup, clamped to the knot range."""
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x1, y1), (x2, y2) in zip(table, table[1:]):
        if x1 <= x <= x2:
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    return table[-1][1]


def _table_inverse(table, target, context):
    """Invert a piecewise-linear table at ``target``.

    Mirrors the kernel's linear interpolator, which extrapolates the first
    or last segment past the table ends: a segment containing ``target``
    wins, otherwise the nearest end segment extrapolates. Flat tables have
    no inverse and raise E2005 unless ``target`` already equals their
    constant value.
    """
    for (x1, y1), (x2, y2) in zip(table, table[1:]):
        if y1 == y2:
            continue
        if min(y1, y2) <= target <= max(y1, y2):
            return x1 + (x2 - x1) * (target - y1) / (y2 - y1)
    if len(table) > 1:
        for (x1, y1), (x2, y2) in ((table[0], table[1]),
                                   (table[-2], table[-1])):
            if y1 != y2:
                return x1 + (x2 - x1) * (target - y1) / (y2 - y1)
    # Every segment is flat.
    if abs(table[0][1] - target) <= 1e-6:
        return table[0][0]
    raise _contract('THMZ-E2005', '{}: flat conductivity-temperature table '
                    'cannot anchor the moisture table'.format(context))


def _moisture_material_props(record, material_uuid, physics):
    """Build the hygrothermal input tuple for one solid material.

    ``physics`` is a :data:`_PhysicsOptions`; the returned tuple's field
    order matches ``_native.solve_hygrothermal``: density, porosity,
    heat capacity, vapor diffusion resistance factor mu, sorption curve
    (phi, w), liquid transport curve (w, D_l), moisture-dependent
    conductivity (w, lambda) with its measurement temperature, and the
    temperature-dependent conductivity (T, lambda) with its measurement
    water content.

    Raises:
        ContractError: THMZ-E2003/E2004 for missing or malformed moisture
            fields, THMZ-E2005 for inconsistent tables, THMZ-E5010 for
            declared properties without kernel support.
    """
    context = 'Material {}'.format(material_uuid)
    hygro = record.find('Solid/HygroThermal')
    for unsupported in ('LiquidTransportationCoefficientRedistribution',
                        'WaterVaporDiffusionResistanceFactorMoistureDependent',
                        'EnthalpyTemperatureDependent'):
        if hygro.find(unsupported) is not None:
            raise _contract('THMZ-E5010', '{}: {} is unsupported'.format(
                context, unsupported))
    density = _hygro_scalar(hygro, 'BulkDensity', material_uuid)
    if density <= 0:
        raise _contract('THMZ-E2004', '{}: BulkDensity must be positive '
                        '(kg/m3); received {!r}'.format(context, density))
    porosity = _hygro_scalar(hygro, 'Porosity', material_uuid)
    if not 0 < porosity <= 1:
        raise _contract('THMZ-E2004', '{}: Porosity must be in (0, 1]; '
                        'received {!r}'.format(context, porosity))
    heat_capacity = _hygro_scalar(hygro, 'SpecificHeatCapacityDry',
                                  material_uuid)
    if heat_capacity <= 0:
        raise _contract('THMZ-E2004', '{}: SpecificHeatCapacityDry must be '
                        'positive (J/kg.K); received {!r}'.format(
                            context, heat_capacity))
    diffusion = _hygro_scalar(hygro, 'WaterVaporDiffusionResistanceFactor',
                              material_uuid)
    if diffusion <= 0:
        raise _contract('THMZ-E2004', '{}: WaterVaporDiffusionResistanceFactor '
                        'must be positive; received {!r}'.format(
                            context, diffusion))
    sorption = _hygro_table(hygro, 'MoistureStorageFunction', material_uuid)
    if not sorption:
        raise _contract('THMZ-E2003', '{}: MoistureStorageFunction table is '
                        'required for hygrothermal solves'.format(context))
    if not all(0 <= phi <= 1 and water >= 0 for phi, water in sorption):
        raise _contract('THMZ-E2004', '{}: MoistureStorageFunction requires '
                        '0 <= humidity <= 1 and water content >= 0'
                        .format(context))
    liquid = ()
    needs_liquid = (not physics.exclude_liquid_transport
                    or not physics.exclude_capillary_conduction)
    liquid_table = _hygro_table(
        hygro, 'LiquidTransportationCoefficientSuction', material_uuid)
    if needs_liquid:
        if not liquid_table:
            raise _contract('THMZ-E2004', '{}: '
                            'LiquidTransportationCoefficientSuction is '
                            'required when liquid transport or capillary '
                            'conduction is enabled'.format(context))
        saturation = max(water for _phi, water in sorption)
        if abs(liquid_table[-1][0] - saturation) > \
                1e-9 * max(1.0, saturation):
            raise _contract('THMZ-E2005', '{}: liquid transport table '
                            'maximum water content must equal the sorption '
                            'saturation content'.format(context))
        liquid = liquid_table
    lambda_water, lambda_temperature = (), ()
    lambda_moisture_measured_temp = 0.0
    lambda_water_reference = 0.0
    if physics.variable_conductivity:
        lambda_water = _hygro_table(
            hygro, 'ThermalConductivityMoistureDependent', material_uuid)
        lambda_temperature = _hygro_table(
            hygro, 'ThermalConductivityTemperatureDependent', material_uuid)
        if not lambda_water or not lambda_temperature:
            raise _contract('THMZ-E2004', '{}: moisture- and '
                            'temperature-dependent conductivity tables are '
                            'required when variable conductivity is enabled'
                            .format(context))
        if lambda_water[0][0] < 0:
            raise _contract('THMZ-E2004', '{}: '
                            'ThermalConductivityMoistureDependent water '
                            'content must be non-negative'.format(context))
        saturation = max(water for _phi, water in sorption)
        if abs(lambda_water[-1][0] - saturation) > \
                1e-9 * max(1.0, saturation):
            raise _contract('THMZ-E2005', '{}: '
                            'ThermalConductivityMoistureDependent maximum '
                            'water content {!r} must equal '
                            'MoistureStorageFunction saturation content {!r}'
                            .format(context, lambda_water[-1][0], saturation))
        if any(value <= 0 for _x, value in lambda_water) or \
                any(value <= 0 for _x, value in lambda_temperature):
            raise _contract('THMZ-E2004', '{}: conductivity tables must be '
                            'positive'.format(context))
        # HygroThermFEM v1.0.80 keys moisture conductivity directly by water
        # content w [kg/m3]. Both 1D tables must agree at each other's
        # measurement point (abs 1e-6): lambda_water at its first knot w0,
        # and lambda_temperature inverted for the temperature yielding that
        # conductivity.
        lambda_water_reference = lambda_water[0][0]
        lambda_moisture_measured_temp = _table_inverse(
            lambda_temperature, lambda_water[0][1],
            context + ' ThermalConductivityTemperatureDependent')
    return (density, porosity, heat_capacity, diffusion,
            tuple(sorption), tuple(liquid),
            tuple(lambda_water), lambda_moisture_measured_temp,
            tuple(lambda_temperature), lambda_water_reference)


def _point_on_segment(point, start, end):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length == 0:
        return False
    px, py = point[0] - start[0], point[1] - start[1]
    projection = (px * dx + py * dy) / length
    distance = abs(px * dy - py * dx) / length
    return (distance <= BOUNDARY_TOLERANCE_MM and
            -BOUNDARY_TOLERANCE_MM <= projection <= length +
            BOUNDARY_TOLERANCE_MM)


def _point_in_polygon(point, vertices):
    inside = False
    for start, end in zip(vertices, vertices[1:] + vertices[:1]):
        if _point_on_segment(point, start, end):
            return True
        if (start[1] > point[1]) != (end[1] > point[1]):
            crossing = start[0] + (point[1] - start[1]) * (
                end[0] - start[0]) / (end[1] - start[1])
            if point[0] < crossing:
                inside = not inside
    return inside


def _segments_overlap(first, second):
    start, end = first
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= BOUNDARY_TOLERANCE_MM:
        return False
    offsets = [(point[0] - start[0], point[1] - start[1])
               for point in second]
    if any(abs(x * dy - y * dx) / length > BOUNDARY_TOLERANCE_MM
           for x, y in offsets):
        return False
    low, high = sorted(x * dx / length + y * dy / length
                       for x, y in offsets)
    return min(length, high) - max(0.0, low) > BOUNDARY_TOLERANCE_MM


def _check_coverage(segments, sides, field):
    """Require a set of mesh segments to cover the given straight sides once."""
    intervals = [[] for _ in sides]
    lengths = [math.dist(start, end) for start, end in sides]
    if not sides or any(length <= BOUNDARY_TOLERANCE_MM for length in lengths):
        raise _contract('THMZ-E3003', '{}: missing or degenerate geometry'.format(field))
    for first, second in segments:
        matched = 0.0
        for i, ((start, end), length) in enumerate(zip(sides, lengths)):
            dx, dy = (end[0] - start[0]) / length, (end[1] - start[1]) / length
            offsets = [(p[0] - start[0], p[1] - start[1])
                       for p in (first, second)]
            if any(abs(x * dy - y * dx) > BOUNDARY_TOLERANCE_MM
                   for x, y in offsets):
                continue
            low, high = sorted(x * dx + y * dy for x, y in offsets)
            low, high = max(0.0, low), min(length, high)
            if high > low:
                intervals[i].append((low, high))
                matched += high - low
        if abs(matched - math.dist(first, second)) > BOUNDARY_TOLERANCE_MM:
            raise _contract('THMZ-E3004', '{}: mesh perimeter leaves model geometry'.format(field))
    for spans, length in zip(intervals, lengths):
        cursor = 0.0
        for low, high in sorted(spans):
            if abs(low - cursor) > BOUNDARY_TOLERANCE_MM:
                raise _contract('THMZ-E3005', '{}: mesh coverage has a gap or overlap'.format(field))
            cursor = high
        if abs(cursor - length) > BOUNDARY_TOLERANCE_MM:
            raise _contract('THMZ-E3005', '{}: incomplete mesh coverage'.format(field))


def _read_archive(path):
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        raise _contract('THMZ-E1002', 'THMZ exceeds the 128 MiB input limit')
    snapshot = path.read_bytes()
    if len(snapshot) > MAX_ARCHIVE_BYTES:
        raise _contract('THMZ-E1002', 'THMZ exceeds the 128 MiB input limit')
    try:
        with zipfile.ZipFile(BytesIO(snapshot)) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise _contract('THMZ-E1003', 'THMZ contains duplicate archive members')
            # ponytail: bounded in-memory archive; stream for larger models.
            if sum(i.file_size for i in archive.infolist()) > MAX_ARCHIVE_BYTES:
                raise _contract('THMZ-E1002', 'THMZ exceeds the 128 MiB baseline limit')
            members = {name: archive.read(name) for name in names}
    except zipfile.BadZipFile as error:
        raise _contract('THMZ-E1006', 'Invalid THMZ ZIP archive: {}'.format(error)) from error
    provenance = members.get('pyHygroTherm.json')
    if provenance is not None:
        try:
            provenance = json.loads(provenance)
        except (ValueError, UnicodeError) as error:
            raise _contract('THMZ-E1101',
                            'pyHygroTherm.json: invalid JSON') from error
        contract_version = provenance.get('contract_version')
        if contract_version is not None:
            if (not isinstance(contract_version, int)
                    or isinstance(contract_version, bool)
                    or contract_version < 0):
                raise _contract(
                    'THMZ-E1101', 'pyHygroTherm.json: contract_version must '
                    'be a non-negative integer')
            if contract_version // 1000 not in (1, CONTRACT_VERSION // 1000):
                raise _contract(
                    'THMZ-E1102', 'pyHygroTherm.json: contract major {} is '
                    'unsupported; supported majors are 1 and {}'.format(
                        contract_version // 1000, CONTRACT_VERSION // 1000))
    if 'CMALibrary.xml' in members:
        raise _contract('THMZ-E5011', 'CMALibrary.xml: glazing systems are '
                        'unsupported')
    roots = {}
    for name in ('Model.xml', 'Mesh.xml', 'Materials.xml', 'SteadyStateBC.xml'):
        # SteadyStateBC.xml is optional for transient archives (contract 4.7);
        # mode-aware validation in _inputs requires it where it applies.
        if name not in members:
            if name == 'SteadyStateBC.xml':
                continue
            raise _contract('THMZ-E1004', 'THMZ is missing {}'.format(name))
        content = members[name]
        if b'<!DOCTYPE' in content.upper() or b'<!ENTITY' in content.upper():
            raise _contract('THMZ-E1005', '{}: XML entities are not supported'.format(name))
        try:
            roots[name] = ET.fromstring(content)
        except ET.ParseError as error:
            raise _contract('THMZ-E1007', '{}: {}'.format(name, error)) from error
    return members, roots, sha256(snapshot).hexdigest()


def _inputs(members, roots):
    for group, fields in (
            ('Nodes/Node', ('index', 'x', 'y')),
            ('Elements/Element', ('index', 'node1', 'node2', 'node3', 'node4',
                                  'materialID')),
            ('BCSegments/Fluxes/Flux', (
                'index', 'node1', 'node2', 'flux1', 'flux2', 'label')),
            ('BCSegments/Temperatures/Temperature', (
                'node', 'temperature', 'label')),
            ('BCSegments/Convections/Convection', (
                'index', 'node1', 'node2', 'filmCoefficient',
                'temperature1', 'temperature2', 'label')),
            ('BCSegments/Radiations/Radiation', (
                'index', 'node1', 'node2', 'filmCoefficient',
                'temperature1', 'temperature2')),
            ('BCSegments/RadiationEnclosures/RadiationEnclosure', (
                'index', 'node1', 'node2', 'condCode', 'emissivity',
                'temperature'))):
        for item in roots['Mesh.xml'].findall('Case/' + group):
            for field in fields:
                if item.findtext(field) is None:
                    raise _contract('THMZ-E2003', 'Mesh.xml {}: missing {}'.format(
                        group, field))
    model = fem.therm_model.from_string(
        members['Model.xml'].decode('utf-8-sig'))
    mesh = fem.mesh.from_string(members['Mesh.xml'].decode('utf-8-sig'))
    if model is None or mesh is None:
        raise _contract('THMZ-E2005', 'Model.xml or Mesh.xml could not be decoded')
    options = model.properties.calculation_options
    calculation_mode = options.calculation_mode
    transient_mode = calculation_mode == fem.CalculationMode.Transient
    if calculation_mode not in (fem.CalculationMode.SteadyState,
                                fem.CalculationMode.Transient):
        raise _contract('THMZ-E2005', 'Model.xml: unsupported '
                        'CalculationMode {!r}'.format(calculation_mode))
    simulate_moisture = bool(options.simulate_moisture)
    if not options.simulate_thermal:
        raise _contract('THMZ-E5003', 'Model.xml: SimulateThermal must be '
                        'true (moisture-only solves are unsupported)')
    if simulate_moisture and not transient_mode:
        raise _contract('THMZ-E5003', 'Model.xml: hygrothermal solves '
                        'require Transient CalculationMode')
    modeling = options.modeling_options
    if modeling is None:
        # A missing ModelingOptions block means every moisture mechanism is
        # excluded, matching the THERM writer defaults.
        physics = _PhysicsOptions(True, True, True, True, True, False)
    else:
        exclude_conductivity = (
            modeling.exclude_thermal_conductivity_moisture_dependent,
            modeling.exclude_thermal_conductivity_temperature_dependent)
        if exclude_conductivity[0] != exclude_conductivity[1]:
            raise _contract('THMZ-E5010', 'Model.xml: moisture- and '
                            'temperature-dependent thermal conductivity '
                            'must be excluded or enabled together')
        physics = _PhysicsOptions(
            exclude_liquid_transport=
            modeling.exclude_water_liquid_transportation,
            exclude_evaporation_heat=modeling.exclude_heat_of_evaporation,
            exclude_capillary_conduction=
            modeling.exclude_capillary_conduction,
            exclude_vapor_conduction=
            modeling.exclude_vapor_diffusion_conduction,
            exclude_fusion_heat=modeling.exclude_latent_heat_of_fusion,
            variable_conductivity=not exclude_conductivity[0])
    if not simulate_moisture:
        if not all(physics[:5]):  # the five Exclude* flags
            raise _contract('THMZ-E5003', 'Model.xml: moisture physics '
                            'options must all be excluded for dry solves')
        if physics.variable_conductivity:
            raise _contract('THMZ-E5010', 'Model.xml: variable thermal '
                            'conductivity options must be excluded for dry '
                            'solves')
    if len(mesh.cases) != 1:
        raise _contract('THMZ-E5014', 'Mesh.xml must contain exactly one Case')
    case = mesh.cases[0]
    if (case.model_type != fem.RunType.UFactor or case.glazing_case is not None
            or case.spacer_case is not None):
        raise _contract('THMZ-E5011', 'Mesh.xml: only a plain U-factor mesh case is supported')
    if not case.nodes or not case.elements:
        raise _contract('THMZ-E2003', 'Mesh.xml requires nodes and Q4 elements')
    polygon_xmls = roots['Model.xml'].findall('Polygons/Polygon')
    if (not polygon_xmls or len(polygon_xmls) != len(model.polygons)
            or any(polygon.findtext('Type') != 'Material'
                   for polygon in polygon_xmls)):
        raise _contract('THMZ-E5011', 'Model.xml: only material polygons are supported')
    if simulate_moisture:
        # Validate referenced wet scalars before the data layer's stod can
        # discard their material/field context. Dry parsing is unchanged.
        referenced_materials = {
            (polygon.findtext('MaterialUUID') or '').casefold()
            for polygon in polygon_xmls}
        for record in roots['Materials.xml'].findall('Material'):
            material_uuid = (record.findtext('UUID') or '').casefold()
            hygro = record.find('Solid/HygroThermal')
            if hygro is not None and material_uuid in referenced_materials:
                for tag in ('BulkDensity', 'Porosity', 'SpecificHeatCapacityDry',
                            'WaterVaporDiffusionResistanceFactor'):
                    _hygro_scalar(hygro, tag, material_uuid)
    database = fem.MaterialsLibrary()
    database.from_string(members['Materials.xml'].decode('utf-8-sig'))
    material_id_by_uuid, material_by_uuid = {}, {}
    moisture_by_uuid = {}
    cavity_model_mappings = []
    polygon_by_uuid, polygon_geometries = {}, []
    frame_cavity_boundaries = []
    for polygon, polygon_xml in zip(model.polygons, polygon_xmls):
        polygon_uuid = polygon_xml.findtext('UUID')
        material_uuid = polygon_xml.findtext('MaterialUUID')
        if not polygon_uuid or not material_uuid:
            raise _contract('THMZ-E2003', 'Model.xml: polygon and material UUIDs are required')
        polygon_uuid = polygon_uuid.casefold()
        material_uuid = material_uuid.casefold()
        if polygon_uuid in polygon_by_uuid:
            raise _contract('THMZ-E2005', 'Model.xml: polygon UUIDs must be unique')
        if (not polygon.material_uuid
                or polygon.material_uuid.casefold() != material_uuid):
            raise _contract('THMZ-E2005', 'Model.xml: polygon material UUID does not match its record')
        if polygon.glazing_system is not None:
            raise _contract('THMZ-E5011', 'Model.xml: glazing systems are not supported')
        if material_uuid not in material_id_by_uuid:
            material_id_by_uuid[material_uuid] = len(material_id_by_uuid) + 1
            material_xml = [m for m in roots['Materials.xml'].findall('Material')
                            if (m.findtext('UUID') or '').casefold() == material_uuid]
            if len(material_xml) != 1:
                raise _contract('THMZ-E2003', 'Polygon {}: missing material {}'.format(
                    polygon.id, material_uuid))
            record = material_xml[0]
            cavity = record.find('Cavity')
            if cavity is not None:
                if record.find('Solid') is not None:
                    raise _contract('THMZ-E2002', 'Material {}: both Solid and Cavity are set'
                                     .format(material_uuid))
                standard = cavity.findtext('CavityStandard')
                gas = cavity.findtext('Gas')
                if standard == 'NFRC':
                    raise _contract('THMZ-E5012', 'Material {}: NFRC must be exported by '
                                     'Fairyfly-Next as ISO15099 with request '
                                     'metadata'.format(material_uuid))
                if standard not in ('CEN', 'ISO15099', 'ISO15099Ventilated'):
                    raise _contract('THMZ-E5012', 'Material {}: unsupported cavity model {}'.format(
                        material_uuid, standard))
                if gas not in ('Air', 'Argon', 'Krypton', 'Xenon'):
                    raise _contract('THMZ-E2005', 'Material {}: unsupported cavity gas {}'.format(
                        material_uuid, gas))
                e1 = _fraction(_xml_number(cavity, 'EmissivitySide1',
                                           'Cavity EmissivitySide1'),
                               'Cavity EmissivitySide1')
                e2 = _fraction(_xml_number(cavity, 'EmissivitySide2',
                                           'Cavity EmissivitySide2'),
                               'Cavity EmissivitySide2')
                material_by_uuid[material_uuid] = _MaterialSpec(
                    0.0, e1, e2, standard, gas, '', False, 1.0, 101325.0)
            else:
                hygro = record.find('Solid/HygroThermal')
                if hygro is None:
                    raise _contract('THMZ-E2003', 'Material {}: missing '
                                    'HygroThermal record'.format(
                                        material_uuid))
                material = database.by_uuid(
                    record.findtext('UUID')).data.hygro_thermal
                conductivity = material.thermal_conductivity_dry
                if conductivity is None:
                    if not (simulate_moisture
                            and physics.variable_conductivity):
                        raise _contract('THMZ-E2003', 'Material {}: missing '
                                        'ThermalConductivityDry'.format(
                                            material_uuid))
                    # Variable-conductivity materials may omit the dry
                    # constant; the binding leaves it unset.
                    conductivity = 0.0
                conductivity = _finite(
                    conductivity,
                    'Material {} ThermalConductivityDry'.format(material_uuid))
                if conductivity <= 0 and not (simulate_moisture
                                              and physics.variable_conductivity):
                    raise _contract('THMZ-E2004', 
                        'Material {}: ThermalConductivityDry must be positive (W/m.K)'
                        .format(material_uuid))
                if (material.thermal_conductivity_temperature_dependent
                        or material.thermal_conductivity_moisture_dependent):
                    if not (simulate_moisture
                            and physics.variable_conductivity):
                        raise _contract('THMZ-E5010', 
                            'Material {}: only constant dry thermal conductivity is '
                            'supported'.format(material_uuid))
                if simulate_moisture:
                    moisture_by_uuid[material_uuid] = _moisture_material_props(
                        record, material_uuid, physics)
                emissivity_path = 'Solid/Optical/Integrated/Infrared/Emissivity-{}'
                emissivity_front = record.findtext(
                    emissivity_path.format('Front'))
                emissivity_front = 0.9 if emissivity_front is None else _fraction(
                    _xml_number(record, emissivity_path.format('Front'),
                                'Material {} Front Emissivity'.format(material_uuid)),
                    'Material {} Front Emissivity'.format(material_uuid))
                emissivity_back = record.findtext(
                    emissivity_path.format('Back'))
                emissivity_back = (emissivity_front if emissivity_back is None else
                                   _fraction(_xml_number(
                                       record, emissivity_path.format('Back'),
                                       'Material {} Back Emissivity'.format(
                                           material_uuid)),
                                       'Material {} Back Emissivity'.format(
                                           material_uuid)))
                material_by_uuid[material_uuid] = _MaterialSpec(
                    conductivity, emissivity_front, emissivity_back,
                    '', '', '', False, 1.0, 101325.0)
        points = [(_xml_number(point, 'x', 'Polygon x'),
                   _xml_number(point, 'y', 'Polygon y'))
                  for point in polygon_xml.findall('Points/Point')]
        if len(points) < 3:
            raise _contract('THMZ-E2003', 'Polygon {}: at least three points are required'.format(
                polygon.id))
        sides = list(zip(points, points[1:] + points[:1]))
        if any(math.dist(start, end) <= BOUNDARY_TOLERANCE_MM
               for start, end in sides):
            raise _contract('THMZ-E3003', 'Polygon {}: degenerate perimeter'.format(polygon.id))
        material_spec = material_by_uuid[material_uuid]
        local_emissivities = False
        cavity_height, cavity_pressure = 1.0, 101325.0
        cavity_uuid = polygon_xml.findtext('CavityUUID')
        if cavity_uuid:
            if not material_spec.cavity_standard:
                raise _contract('THMZ-E2005', 'Polygon {}: CavityUUID uses a solid material'
                                 .format(polygon.id))
            records = [item for item in roots['Model.xml'].findall(
                'Cavities/Cavity') if (item.findtext('UUID') or '').casefold()
                == cavity_uuid.casefold()]
            if len(records) != 1:
                raise _contract('THMZ-E2005', 'Polygon {}: unresolved CavityUUID {}'.format(
                    polygon.id, cavity_uuid))
            record = records[0]
            cavity_height = _xml_number(record, 'ActualHeight',
                                        'Cavity ActualHeight') / 1000.0
            cavity_pressure = _xml_number(record, 'Pressure', 'Cavity Pressure')
            if cavity_height <= 0 or cavity_pressure <= 0:
                raise _contract('THMZ-E2005', 'Cavity {}: height and pressure must be positive'
                                 .format(cavity_uuid))
            local = record.findtext('LocalEmissivities')
            if local not in ('true', 'false'):
                raise _contract('THMZ-E2005', 'Cavity {}: invalid LocalEmissivities'.format(
                    cavity_uuid))
            local_emissivities = local == 'true'
            if not local_emissivities:
                e1 = _fraction(_xml_number(record, 'Emissivity1',
                                           'Cavity Emissivity1'),
                               'Cavity Emissivity1')
                e2 = _fraction(_xml_number(record, 'Emissivity2',
                                           'Cavity Emissivity2'),
                               'Cavity Emissivity2')
                material_spec = material_spec._replace(
                    emissivity_front=e1, emissivity_back=e2)
        polygon_by_uuid[polygon_uuid] = material_uuid
        polygon_geometries.append({
            'uuid': polygon_uuid, 'material_uuid': material_uuid,
            'material_id': material_id_by_uuid[material_uuid],
            'material_spec': material_spec._replace(
                region_key=polygon_uuid,
                local_emissivities=local_emissivities,
                cavity_height=cavity_height,
                cavity_pressure=cavity_pressure),
            'points': points, 'sides': sides,
        })

    if 'FairyflyNext.json' in members:
        try:
            exported = json.loads(members['FairyflyNext.json'])[
                'cavity_model_mappings']
            if not isinstance(exported, list):
                raise _contract('THMZ-E2002', 'mappings must be a list')
            seen = set()
            for item in exported:
                uuid = item['material_uuid'].casefold()
                if (uuid in seen or uuid not in material_by_uuid
                        or material_by_uuid[uuid][3] != 'ISO15099'
                        or material_by_uuid[uuid][4] != 'Air'
                        or item['requested'] != 'NFRC'
                        or item['effective'] != 'ISO15099'
                        or item['reference'] !=
                        'LBNL NFRC Simulation Manual 6.3.6'):
                    raise _contract('THMZ-E2005', 'mapping does not match cavity material')
                seen.add(uuid)
                cavity_model_mappings.append({
                    'material_uuid': item['material_uuid'],
                    'requested': 'NFRC', 'effective': 'ISO15099',
                    'reference': 'LBNL NFRC Simulation Manual 6.3.6',
                })
        except (ValueError, TypeError, KeyError, AttributeError,
                UnicodeError) as error:
            raise _contract('THMZ-E2005', 'FairyflyNext.json: invalid cavity mapping') from error

    mesh_material_ids = {element.material_id for element in case.elements}
    if None in mesh_material_ids or any(value <= 0 for value in mesh_material_ids):
        raise _contract('THMZ-E3001', 'Mesh.xml elements must use positive materialID values')
    if len(material_id_by_uuid) == 1:
        if len(mesh_material_ids) != 1:
            raise _contract('THMZ-E3002', 'Mesh.xml: one material requires one materialID')
        # Single-material archives historically used any positive materialID.
        mesh_id = next(iter(mesh_material_ids))
        uuid = next(iter(material_id_by_uuid))
        uuid_by_material_id = {mesh_id: uuid}
        for polygon in polygon_geometries:
            polygon['material_id'] = mesh_id
    else:
        expected_ids = set(range(1, len(material_id_by_uuid) + 1))
        if mesh_material_ids != expected_ids:
            raise _contract('THMZ-E3002', 
                'Mesh.xml: materialID must follow first-seen polygon material '
                'UUID order')
        uuid_by_material_id = {
            material_id: material_uuid
            for material_uuid, material_id in material_id_by_uuid.items()}

    # THMZ element refs are positions; Node.index is an independent label.
    nodes = [(i, _finite(n.x, 'Node x'), _finite(n.y, 'Node y'))
             for i, n in enumerate(case.nodes)]
    if len(set(n.index for n in case.nodes)) != len(nodes):
        raise _contract('THMZ-E3002', 'Mesh.xml contains duplicate node labels')
    if len(set((n[1], n[2]) for n in nodes)) != len(nodes):
        raise _contract('THMZ-E3003', 'Mesh.xml contains coincident nodes')
    if len(set(e.index for e in case.elements)) != len(case.elements):
        raise _contract('THMZ-E3002', 'Mesh.xml contains duplicate element indices')
    quads, materials = [], []
    edges, adjacency = Counter(), [set() for _ in nodes]
    edge_material_ids = {}
    material_edges = {material_id: set() for material_id in uuid_by_material_id}
    directions = Counter()
    for element in case.elements:
        quad = (element.node1, element.node2, element.node3, element.node4)
        if (len(set(quad)) != 4 or any(n is None or n < 0 or n >= len(nodes)
                                      for n in quad)):
            raise _contract('THMZ-E3001', 'Element {}: invalid Q4 node indices'.format(
                element.index))
        material_id = element.material_id
        if material_id not in uuid_by_material_id:
            raise _contract('THMZ-E3001', 'Element {}: unresolved materialID {}'.format(
                element.index, material_id))
        points = [nodes[n][1:] for n in quad]
        for i in range(4):
            a, b, c = (points[(i + j) % 4] for j in range(3))
            cross = ((b[0] - a[0]) * (c[1] - b[1])
                     - (b[1] - a[1]) * (c[0] - b[0]))
            if not math.isfinite(cross) or cross <= 0:
                raise _contract('THMZ-E3004', 'Element {}: Q4 must be convex and CCW'.format(
                    element.index))
            left, right = quad[i], quad[(i + 1) % 4]
            edge = tuple(sorted((left, right)))
            edges[edge] += 1
            edge_material_ids.setdefault(edge, set()).add(material_id)
            material_edges[material_id].add(edge)
            directions[left, right] += 1
            adjacency[left].add(right)
            adjacency[right].add(left)
        quads.append(quad)
    if len(set(quads)) != len(quads) or any(n > 2 for n in edges.values()):
        raise _contract('THMZ-E3005', 'Mesh.xml contains duplicate or nonmanifold elements')
    if any(count > 1 for count in directions.values()):
        raise _contract('THMZ-E3005', 'Mesh.xml: shared Q4 edges must have opposite directions')
    exterior = [edge for edge, count in edges.items() if count == 1]
    if any(count != 2 for count in Counter(n for e in exterior for n in e).values()):
        raise _contract('THMZ-E3005', 'Mesh.xml: nonmanifold perimeter nodes')
    visited, pending = set(), [0]
    while pending:
        node = pending.pop()
        if node not in visited:
            visited.add(node)
            pending.extend(adjacency[node] - visited)
    if len(visited) != len(nodes):
        raise _contract('THMZ-E3006', 'Mesh.xml contains disconnected or unused nodes')
    segments = case.bc_segments
    mesh_case_xml = roots['Mesh.xml'].find('Case')
    bc_xml = mesh_case_xml.find('BCSegments')
    if bc_xml is not None:
        _only_fields(bc_xml, {
            'Fluxes', 'Temperatures', 'Convections', 'Radiations',
            'RadiationEnclosures'}, 'Mesh.xml BCSegments')
    temperature_nodes = {}
    for fixed in segments.temperatures or ():
        node = fixed.node
        if node < 0 or node >= len(nodes):
            raise _contract('THMZ-E3001', 'Mesh.xml Temperatures: node index '
                            '{} out of range'.format(node))
        temperature = _finite(fixed.temperature,
                              'Temperatures temperature')
        if node in temperature_nodes:
            raise _contract('THMZ-E3001', 'Mesh.xml Temperatures: node {} is '
                            'declared twice'.format(node))
        temperature_nodes[node] = (temperature, str(fixed.label))
    segment_fluxes = []
    for flux in segments.fluxes or ():
        flux1 = _finite(flux.flux1, 'Flux flux1')
        flux2 = _finite(flux.flux2, 'Flux flux2')
        if not math.isclose(flux1, flux2, rel_tol=1e-9, abs_tol=1e-8):
            raise _contract('THMZ-E5015', 'Mesh.xml: non-uniform flux along a '
                            'segment is unsupported')
        segment_fluxes.append((flux.node1, flux.node2, flux1, flux.label))
    segment_radiations = []
    for radiation in segments.radiations or ():
        coefficient = _finite(radiation.film_coefficient,
                              'Radiation filmCoefficient')
        temperature1 = _finite(radiation.temperature1,
                               'Radiation temperature1')
        temperature2 = _finite(radiation.temperature2,
                               'Radiation temperature2')
        if not math.isclose(temperature1, temperature2,
                            rel_tol=1e-9, abs_tol=1e-8):
            raise _contract('THMZ-E5015', 'Mesh.xml: non-uniform radiant '
                            'temperature along a segment is unsupported')
        if coefficient < 0 or coefficient > STEFAN_BOLTZMANN:
            raise _contract('THMZ-E2004', 'Mesh.xml: Radiation filmCoefficient '
                            '(emissivity times Stefan-Boltzmann) must be in '
                            '[0, {}]'.format(STEFAN_BOLTZMANN))
        if coefficient:
            emissivity = coefficient / STEFAN_BOLTZMANN
            segment_radiations.append(
                (radiation.node1, radiation.node2, emissivity, temperature1))
    for enclosure in segments.radiation_enclosures or ():
        emissivity = _finite(enclosure.emissivity, 'Radiation emissivity')
        if emissivity != 0:
            raise _contract('THMZ-E5006', 'Mesh.xml: active Radiation '
                            'enclosures are unsupported')

    transient_material_props = {}   # polygon uuid -> (density, heat_capacity)
    moisture_material_props = {}    # polygon uuid -> HygrothermalMaterialInput | None
    for polygon in polygon_geometries:
        if not transient_mode:
            continue
        if simulate_moisture:
            # Wet transient: solids carry the parsed hygrothermal record,
            # cavity materials map to None (no moisture extension).
            moisture_material_props[polygon['uuid']] = (
                None if polygon['material_spec'].cavity_standard
                else moisture_by_uuid[polygon['material_uuid']])
            continue
        if polygon['material_spec'].cavity_standard:
            continue
        material_uuid = polygon['material_uuid']
        record = [m for m in roots['Materials.xml'].findall('Material')
                  if (m.findtext('UUID') or '').casefold() == material_uuid][0]
        density = _xml_number(
            record, 'Solid/HygroThermal/BulkDensity',
            'Material {} BulkDensity'.format(material_uuid))
        heat_capacity = _xml_number(
            record, 'Solid/HygroThermal/SpecificHeatCapacityDry',
            'Material {} SpecificHeatCapacityDry'.format(material_uuid))
        if density <= 0:
            raise _contract('THMZ-E2004', 'Material {}: BulkDensity must be '
                            'positive (kg/m3) for transient solves'
                            .format(material_uuid))
        if heat_capacity <= 0:
            raise _contract('THMZ-E2004', 'Material {}: SpecificHeatCapacityDry '
                            'must be positive (J/kg.K) for transient solves'
                            .format(material_uuid))
        transient_material_props[polygon['uuid']] = (density, heat_capacity)

    boundary_by_id = {}
    for boundary in roots['Model.xml'].findall('Boundaries/Boundary'):
        boundary_id = boundary.findtext('ID')
        name = boundary.findtext('Name')
        if not boundary_id or not name or boundary_id in boundary_by_id:
            raise _contract('THMZ-E2005', 'Model.xml: boundary IDs and names must be unique')
        material_side_xml = boundary.find('MaterialSide')
        material_side = ('Front' if material_side_xml is None else
                         (material_side_xml.text or ''))
        if material_side not in ('Front', 'Back'):
            raise _contract('THMZ-E2005', 'Boundary {}: MaterialSide must be Front or Back'
                             .format(boundary_id))
        if boundary.findtext('Type') == 'Frame Cavity':
            frame_cavity_boundaries.append((boundary, material_side))
            continue  # Internal cavity radiation is handled by the gas model.
        if boundary.findtext('Type') != 'Boundary Condition':
            raise _contract('THMZ-E5011', 'Boundary {}: unsupported boundary type'.format(
                boundary_id))
        neighbors = [child.text for child in boundary
                     if child.tag.startswith('NeighborPolygonUUID')]
        if (len(neighbors) != 1 or not neighbors[0]
                or neighbors[0].casefold() not in polygon_by_uuid):
            raise _contract('THMZ-E4002', 'Boundary {}: neighbor polygon UUID is unresolved'
                             .format(boundary_id))
        start, end = boundary.find('StartPoint'), boundary.find('EndPoint')
        if start is None or end is None:
            raise _contract('THMZ-E2003', 'Boundary {}: missing line geometry'.format(boundary_id))
        points = (
            (_xml_number(start, 'x', 'Boundary start x'),
             _xml_number(start, 'y', 'Boundary start y')),
            (_xml_number(end, 'x', 'Boundary end x'),
             _xml_number(end, 'y', 'Boundary end y'))
        )
        if points[0] == points[1]:
            raise _contract('THMZ-E3003', 'Boundary {}: zero-length line geometry'.format(
                boundary_id))
        neighbor_uuid = neighbors[0].casefold()
        neighbor = next(p for p in polygon_geometries
                        if p['uuid'] == neighbor_uuid)
        if not any(all(_point_on_segment(point, *side) for point in points)
                   for side in neighbor['sides']):
            raise _contract('THMZ-E4003', 'Boundary {}: geometry is not on neighboring '
                             'polygon {}'.format(boundary_id, neighbor_uuid))
        field = 'Boundary {} surface Emissivity'.format(boundary_id)
        emissivity = _fraction(_xml_number(
            boundary, 'ThermalEmissionProperties/Emissivity', field), field)
        boundary_by_id[boundary_id] = {
            'name': name, 'points': points, 'polygon_uuid': neighbor_uuid,
            'emissivity': emissivity,
            'has_transient': boundary.find('TransientData') is not None}

    steady_bc_root = roots.get('SteadyStateBC.xml')
    steady_names = {b['name'] for b in boundary_by_id.values()
                    if not b['has_transient']}
    if not transient_mode:
        steady_names = {b['name'] for b in boundary_by_id.values()}
    if steady_names and steady_bc_root is None:
        raise _contract('THMZ-E1004', 'THMZ is missing SteadyStateBC.xml')
    condition_values = {}
    if steady_names:
        if steady_bc_root.tag != 'BoundaryConditions':
            raise _contract('THMZ-E2002', 'SteadyStateBC.xml: expected '
                            'BoundaryConditions root')
        _only_fields(steady_bc_root, {'Version', 'BoundaryCondition'},
                     'SteadyStateBC.xml')
        bc_records = steady_bc_root.findall('BoundaryCondition')
        bc_names = Counter(record.findtext('Name') for record in bc_records)
        for name in steady_names:
            matches = [record for record in bc_records
                       if record.findtext('Name') == name]
            if len(matches) != 1 or bc_names[name] != 1:
                raise _contract('THMZ-E4004', 'Boundary {}: name must map to '
                                'one SteadyStateBC record'.format(name))
            condition_values[name] = _condition_values(matches[0])

    glazing_origin = roots['Model.xml'].find('GlazingOrigin')
    if glazing_origin is None:
        raise _contract('THMZ-E2003', 'Model.xml: missing GlazingOrigin')
    origin_x = _xml_number(glazing_origin, 'x', 'GlazingOrigin x')
    origin_y = _xml_number(glazing_origin, 'y', 'GlazingOrigin y')
    physical_nodes = [(node[1] * 1000 + origin_x,
                       node[2] * 1000 + origin_y) for node in nodes]
    polygon_edges = {}
    for polygon in polygon_geometries:
        material_id = polygon['material_id']
        boundary_edges = {
            edge for edge in material_edges[material_id]
            if any(all(_point_on_segment(physical_nodes[node], *side)
                       for node in edge) for side in polygon['sides'])}
        polygon_edges[polygon['uuid']] = boundary_edges
        _check_coverage(
            [(physical_nodes[a], physical_nodes[b]) for a, b in boundary_edges],
            polygon['sides'], 'Polygon {}'.format(polygon['uuid']))

    for element, quad in zip(case.elements, quads):
        material_id = element.material_id
        points = [physical_nodes[node] for node in quad]
        samples = points + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                             for a, b in zip(points, points[1:] + points[:1])]
        center = (sum(point[0] for point in points) / 4,
                  sum(point[1] for point in points) / 4)
        samples.append(center)
        candidates = [p for p in polygon_geometries
                      if p['material_id'] == material_id]
        if any(not any(_point_in_polygon(point, p['points'])
                       for p in candidates) for point in samples):
            raise _contract('THMZ-E3007', 'Element {}: materialID does not match polygon '
                             'geometry'.format(element.index))
        owners = [p for p in polygon_geometries
                  if _point_in_polygon(center, p['points'])]
        if len(owners) != 1 or owners[0]['material_id'] != material_id:
            raise _contract('THMZ-E3007', 'Element {}: materialID has ambiguous polygon '
                             'ownership'.format(element.index))
        materials.append(owners[0]['material_spec'])

    for index, first in enumerate(polygon_geometries):
        for second in polygon_geometries[index + 1:]:
            for first_side in first['sides']:
                for second_side in second['sides']:
                    if not _segments_overlap(first_side, second_side):
                        continue
                    first_edges = {
                        edge for edge in polygon_edges[first['uuid']]
                        if all(_point_on_segment(physical_nodes[node], *side)
                               for node in edge
                               for side in (first_side, second_side))}
                    second_edges = {
                        edge for edge in polygon_edges[second['uuid']]
                        if all(_point_on_segment(physical_nodes[node], *side)
                               for node in edge
                               for side in (first_side, second_side))}
                    if not first_edges or first_edges != second_edges:
                        raise _contract('THMZ-E3005', 
                            'Polygons {} and {}: shared interface mesh edges '
                            'must use identical nodes'.format(
                                first['uuid'], second['uuid']))
                    for edge in first_edges:
                        expected = {first['material_id'], second['material_id']}
                        if edges[edge] != 2 or not expected.issubset(
                                edge_material_ids[edge]):
                            raise _contract('THMZ-E3005', 
                                'Polygons {} and {}: shared interface must '
                                'have one adjacent element per region'.format(
                                    first['uuid'], second['uuid']))
    # Exterior edge -> list of directed (u, v) as the owning element's edge.
    exterior = {edge for edge, count in edges.items() if count == 1}
    edge_direction = {}
    for element, quad in zip(case.elements, quads):
        material_id = element.material_id
        for i in range(4):
            left, right = quad[i], quad[(i + 1) % 4]
            key = (min(left, right), max(left, right))
            if key in exterior:
                edge_direction[key] = (left, right, material_id)
    convection, fluxes, radiations, fixed_temperatures = [], [], [], []
    edge_bcs = []
    transient_context = None
    if transient_mode:
        transient_context = _transient_boundary_conditions(
            members, roots, options, boundary_by_id, frame_cavity_boundaries,
            exterior, physical_nodes, nodes, condition_values,
            simulate_moisture)
        boundary_segments = transient_context['boundary_segments']
    else:
        (convection, radiations, fluxes, fixed_temperatures, edge_bcs,
         boundary_segments) = _steady_boundary_conditions(
            segments, temperature_nodes, segment_fluxes, segment_radiations,
            boundary_by_id, condition_values, nodes, physical_nodes, edges,
            exterior, edge_direction, uuid_by_material_id, material_by_uuid)
    for key, boundary in boundary_by_id.items():
        _check_coverage(boundary_segments[key], [boundary['points']],
                        'Boundary {}'.format(key))
    cavity_surface_emissivities = {}
    polygons_by_uuid = {polygon['uuid']: polygon
                        for polygon in polygon_geometries}
    polygon_uuids_by_edge = {}
    for uuid, polygon_edges_for_uuid in polygon_edges.items():
        for edge in polygon_edges_for_uuid:
            polygon_uuids_by_edge.setdefault(edge, set()).add(uuid)
    for boundary, material_side in frame_cavity_boundaries:
        neighbor_uuids = [child.text.casefold() for child in boundary
                          if child.tag.startswith('NeighborPolygonUUID')
                          and child.text]
        boundary_id = boundary.findtext('ID')
        if not neighbor_uuids:
            raise _contract('THMZ-E2003', 'Frame Cavity boundary {}: neighbor polygon UUID is '
                             'missing'.format(boundary_id))
        declared_neighbors = set(neighbor_uuids)
        if len(declared_neighbors) != len(neighbor_uuids):
            raise _contract('THMZ-E2005', 'Frame Cavity boundary {}: duplicate neighbor polygon '
                             'UUID'.format(boundary_id))
        start, end = boundary.find('StartPoint'), boundary.find('EndPoint')
        if start is None or end is None:
            raise _contract('THMZ-E2003', 'Frame Cavity boundary {}: missing line geometry'
                             .format(boundary_id))
        points = (
            (_xml_number(start, 'x', 'Frame Cavity start x'),
             _xml_number(start, 'y', 'Frame Cavity start y')),
            (_xml_number(end, 'x', 'Frame Cavity end x'),
             _xml_number(end, 'y', 'Frame Cavity end y')))
        if points[0] == points[1]:
            raise _contract('THMZ-E3003', 'Frame Cavity boundary {}: zero-length line geometry'
                             .format(boundary_id))
        matched = [edge for edge in edges
                   if all(_point_on_segment(physical_nodes[node], *points)
                          for node in edge)]
        if not matched:
            raise _contract('THMZ-E4003', 'Frame Cavity boundary {}: geometry has no matching '
                             'mesh edge'.format(boundary_id))
        for edge in matched:
            actual_neighbors = polygon_uuids_by_edge.get(edge, set())
            if (actual_neighbors != declared_neighbors or
                    len(actual_neighbors) != edges[edge]):
                raise _contract('THMZ-E4002', 
                    'Frame Cavity boundary {}: declared neighbor UUIDs do not '
                    'match mesh adjacency for edge {}'.format(boundary_id, edge))
            adjacent = [polygons_by_uuid[uuid] for uuid in actual_neighbors]
            gases = [polygon for polygon in adjacent
                     if polygon['material_spec'].cavity_standard]
            solids = [polygon for polygon in adjacent
                      if not polygon['material_spec'].cavity_standard]
            if not gases:
                raise _contract('THMZ-E4002', 'Frame Cavity boundary {}: mesh edge {} has no '
                                 'adjacent cavity polygon'.format(boundary_id, edge))
            if not solids:
                continue  # Gas-only perimeter edges have no local solid surface.
            local_gases = [polygon for polygon in gases
                           if polygon['material_spec'].local_emissivities]
            if not local_gases:
                continue
            if len(gases) != 1 or len(solids) != 1:
                raise _contract('THMZ-E4002', 'Frame Cavity boundary {}: expected one adjacent '
                                 'cavity and solid polygon for local emissivity'
                                 .format(boundary_id))
            solid = solids[0]
            emissivity = (solid['material_spec'].emissivity_front
                          if material_side == 'Front'
                          else solid['material_spec'].emissivity_back)
            previous = cavity_surface_emissivities.get(edge)
            if previous is not None and not math.isclose(
                    previous, emissivity, rel_tol=1e-9, abs_tol=1e-12):
                raise _contract('THMZ-E4005', 'Frame Cavity boundary {}: conflicting emissivity '
                                 'for mesh edge {}'.format(boundary_id, edge))
            cavity_surface_emissivities[edge] = emissivity
    required_cavity_edges = {}
    for edge in edges:
        adjacent = [polygons_by_uuid[uuid]
                    for uuid in polygon_uuids_by_edge.get(edge, ())]
        local_gases = [polygon for polygon in adjacent
                       if polygon['material_spec'].cavity_standard
                       and polygon['material_spec'].local_emissivities]
        solids = [polygon for polygon in adjacent
                  if not polygon['material_spec'].cavity_standard]
        if not local_gases or not solids:
            continue
        if (len(local_gases) != 1 or len(solids) != 1
                or len(adjacent) != edges[edge]):
            raise _contract('THMZ-E4002', 'Local cavity {}: mesh edge {} must have one adjacent '
                             'gas and solid polygon'.format(
                                 local_gases[0]['uuid'], edge))
        required_cavity_edges[edge] = local_gases[0]['uuid']
    missing_cavity_edges = (required_cavity_edges.keys() -
                            cavity_surface_emissivities.keys())
    if missing_cavity_edges:
        edge = min(missing_cavity_edges)
        raise _contract('THMZ-E4002', 'Local cavity {}: mesh edge {} is missing Frame Cavity '
                         'coverage'.format(required_cavity_edges[edge], edge))
    if transient_mode:
        if not transient_context['anchored']:
            raise _contract('THMZ-E4006', 'Mesh.xml: all-adiabatic model has '
                            'no temperature anchor')
    elif not convection and not radiations and not fixed_temperatures:
        raise _contract('THMZ-E4006', 'Mesh.xml: all-adiabatic model has no temperature anchor')
    gravity_name = roots['Model.xml'].findtext(
        'Properties/ModelExposure/GravityOrientation') or 'Down'
    gravity = {
        'Down': (0.0, -1.0, 0.0), 'Up': (0.0, 1.0, 0.0),
        'Left': (-1.0, 0.0, 0.0), 'Right': (1.0, 0.0, 0.0),
        'Into Screen': (0.0, 0.0, -1.0),
        'Out Of Screen': (0.0, 0.0, 1.0),
    }.get(gravity_name)
    if gravity is None:
        raise _contract('THMZ-E2005', 'ModelExposure: unsupported GravityOrientation {}'.format(
            gravity_name))
    geometry_context = {
        'polygon_geometries': polygon_geometries,
        'uuid_by_material_id': uuid_by_material_id}
    return (case, nodes, quads, materials, convection, radiations, fluxes,
            fixed_temperatures, edge_bcs,
            gravity, [(a, b, value) for (a, b), value in
                      sorted(cavity_surface_emissivities.items())],
            cavity_model_mappings, transient_mode,
            transient_material_props, transient_context, geometry_context,
            simulate_moisture, physics, moisture_material_props)


def _resolve_segment_boundary(boundary_by_id, label, candidate_points,
                              physical_nodes, what):
    """Resolve a BC segment's model boundary from its label and geometry.

    Fairyfly-Next writes ``label`` equal to ``Model.xml Boundary/ID``;
    THERM 8.1 exports opaque internal segment labels (e.g. ``42``) that
    match no boundary ID (contract section 9). A label that resolves to an
    ID is authoritative once the segment geometry sits on that boundary;
    an unresolvable label falls back to the unique geometric match. A
    resolvable label contradicting the geometry and an opaque label with
    no or multiple geometric candidates are both errors.
    """
    edge_points = tuple(physical_nodes[node] for node in candidate_points)
    candidates = [key for key, boundary in boundary_by_id.items()
                  if all(_point_on_segment(point, *boundary['points'])
                         for point in edge_points)]
    boundary_id = str(label)
    if boundary_id in boundary_by_id:
        if not all(_point_on_segment(point,
                                     *boundary_by_id[boundary_id]['points'])
                   for point in edge_points):
            raise _contract('THMZ-E4003', '{}: boundary label {} does not '
                            'match the segment geometry'.format(
                                what, boundary_id))
        return boundary_id
    if len(candidates) != 1:
        raise _contract('THMZ-E4003', '{}: opaque boundary label {} does '
                        'not resolve to exactly one boundary'.format(
                            what, boundary_id))
    return candidates[0]


def _steady_boundary_conditions(segments, temperature_nodes,
                                segment_fluxes, segment_radiations,
                                boundary_by_id, condition_values, nodes,
                                physical_nodes, edges, exterior,
                                edge_direction, uuid_by_material_id,
                                material_by_uuid):
    """Interpret Mesh.xml BC segments for steady-state solves."""
    # Labelled segments resolve their boundary through the Boundary/ID
    # label or, for THERM-style opaque labels, by unique geometry match;
    # radiation segments resolve by geometry. The same rules keep every
    # exterior edge covered exactly once and every model boundary matched.
    boundary_segments = {key: [] for key in boundary_by_id}
    boundary_kinds = {key: set() for key in boundary_by_id}
    convection, covered, used_boundaries = [], set(), set()
    fluxes, radiations, fixed_temperatures = [], [], []
    edge_bcs = []
    inert_names = {
        name for name, (film, _, flux, environment, _, view, _humidity) in
        condition_values.items()
        if not (film > 0 or flux != 0 or
                (environment != 0 and view != 0))}
    # The Convections group is optional: Dirichlet-, flux- or
    # radiation-only archives carry no convection segments at all.
    for bc in segments.convections or ():
        if (bc.node1 == bc.node2 or bc.node1 < 0 or bc.node2 < 0
                or bc.node1 >= len(nodes) or bc.node2 >= len(nodes)):
            raise _contract('THMZ-E4001', 'Convection {}: invalid node indices'.format(bc.index))
        edge = tuple(sorted((bc.node1, bc.node2)))
        if edges[edge] != 1 or edge in covered:
            raise _contract('THMZ-E4001', 'Convection {}: duplicate or non-exterior edge'.format(
                bc.index))
        boundary_id = _resolve_segment_boundary(
            boundary_by_id, bc.label, (bc.node1, bc.node2), physical_nodes,
            'Convection {}'.format(bc.index))
        covered.add(edge)
        boundary = boundary_by_id[boundary_id]
        boundary_kinds[boundary_id].add('convection')
        edge_points = (physical_nodes[bc.node1], physical_nodes[bc.node2])
        boundary_segments[boundary_id].append(edge_points)
        used_boundaries.add(boundary_id)
        h = _finite(bc.film_coefficient, 'Convection filmCoefficient')
        t1 = _finite(bc.temperature1, 'Convection temperature1')
        t2 = _finite(bc.temperature2, 'Convection temperature2')
        if h < 0 or not math.isclose(t1, t2, rel_tol=1e-9, abs_tol=1e-8):
            raise _contract('THMZ-E2004', 'Convection requires h >= 0 and uniform temperature')
        (expected_h, expected_temperature, flux, environment, radiant_temperature,
         view_factor, _humidity) = condition_values[boundary['name']]
        if not math.isclose(h, expected_h, rel_tol=1e-9, abs_tol=1e-8):
            raise _contract('THMZ-E4005', 'Convection {}: film coefficient disagrees with '
                             'boundary condition {}'.format(bc.index,
                                                            boundary['name']))
        if (not math.isclose(t1, expected_temperature,
                             rel_tol=1e-9, abs_tol=1e-8)
                or not math.isclose(t2, expected_temperature,
                                    rel_tol=1e-9, abs_tol=1e-8)):
            raise _contract('THMZ-E4005', 'Convection {}: temperature disagrees with '
                             'boundary condition {}'.format(bc.index,
                                                            boundary['name']))
        if h > 0:
            convection.append((bc.node1, bc.node2, h, t1, t2))
        if flux != 0:
            fluxes.append((bc.node1, bc.node2, flux))
        surface = boundary['emissivity']
        exchange = 0.0
        if surface and environment and view_factor:
            # Scalar, equal-area diffuse gray exchange; no geometric enclosure.
            exchange = 1 / (1 / surface + 1 / environment + 1 / view_factor - 2)
            radiations.append((bc.node1, bc.node2, exchange,
                               radiant_temperature))
        edge_bcs.append({'kind': 'convection', 'edge': edge,
                         'boundary_id': boundary_id, 'h': h,
                         'air_temperature': t1, 'flux': flux,
                         'exchange': exchange,
                         'radiant_temperature': radiant_temperature})

    # Fixed-temperature node segments: a node's label names the boundary it
    # belongs to, so exterior edges of that boundary whose endpoints are both
    # declared become Dirichlet edges. Neighbouring edges of other boundaries
    # that merely touch a declared node are unaffected.
    node_sets = {}
    for node, (_, label) in temperature_nodes.items():
        node_sets.setdefault(label, set()).add(node)
    claimed_temperature_nodes = set()
    for label, declared in node_sets.items():
        # A label that names a Boundary/ID is authoritative; opaque THERM
        # labels resolve to the unique boundary covering all declared
        # nodes (contract section 9).
        if label in boundary_by_id:
            boundary_id = label
        else:
            candidates = [key for key, boundary in boundary_by_id.items()
                          if all(_point_on_segment(
                              physical_nodes[node], *boundary['points'])
                              for node in declared)]
            if len(candidates) != 1:
                raise _contract('THMZ-E4003', 'Temperatures: opaque '
                                'boundary label {} does not resolve to '
                                'exactly one boundary'.format(label))
            boundary_id = candidates[0]
        boundary = boundary_by_id[boundary_id]
        boundary_kinds[boundary_id].add('temperature')
        for edge in sorted(exterior):
            first, second = edge
            if not all(_point_on_segment(physical_nodes[node],
                                         *boundary['points'])
                       for node in edge):
                continue
            if edge in covered:
                # Claimed by a different segment kind on the same boundary;
                # the per-boundary single-kind check rejects it below.
                continue
            if {first, second} - declared:
                node = min({first, second} - declared)
                raise _contract(
                    'THMZ-E3001', 'Mesh.xml: Temperatures edge {} is missing '
                    'a fixed temperature on node {}'.format(edge, node))
            temperature1 = temperature_nodes[first][0]
            temperature2 = temperature_nodes[second][0]
            if not math.isclose(temperature1, temperature2,
                                rel_tol=1e-9, abs_tol=1e-8):
                raise _contract('THMZ-E5015', 'Mesh.xml: non-uniform fixed '
                                'temperature along a segment is unsupported')
            claimed_temperature_nodes.update((first, second))
            if boundary['name'] not in inert_names:
                raise _contract('THMZ-E4005', 'Boundary {}: fixed-temperature '
                                'segments need an inert boundary condition '
                                'record'.format(boundary['name']))
            material_id = edge_direction[edge][2]
            material_uuid = uuid_by_material_id[material_id]
            if material_by_uuid[material_uuid][3]:
                raise _contract('THMZ-E5015', 'Mesh.xml: fixed temperature on '
                                'a gas cavity edge is unsupported')
            covered.add(edge)
            used_boundaries.add(boundary_id)
            boundary_segments[boundary_id].append(
                (physical_nodes[first], physical_nodes[second]))
            fixed_temperatures.append((first, second, temperature1))
            edge_bcs.append({'kind': 'temperature', 'edge': edge,
                             'boundary_id': boundary_id,
                             'temperature': temperature1,
                             'directed': edge_direction[edge]})
    unclaimed = set(temperature_nodes) - claimed_temperature_nodes
    if unclaimed:
        node = min(unclaimed)
        raise _contract('THMZ-E3001', 'Mesh.xml: Temperatures node {} is not '
                        'part of an exterior edge on its boundary'
                        .format(node))

    # Flux segments are the sole condition on their exterior edges; record
    # cross-check accepts a matching Comprehensive/ConstantFlux value.
    for node1, node2, flux, label in segment_fluxes:
        if (node1 == node2 or node1 < 0 or node2 < 0
                or node1 >= len(nodes) or node2 >= len(nodes)):
            raise _contract('THMZ-E4001', 'Flux {}-{}: invalid node indices'
                            .format(node1, node2))
        edge = tuple(sorted((node1, node2)))
        if edges[edge] != 1 or edge in covered:
            raise _contract('THMZ-E4001', 'Flux {}-{}: duplicate or '
                            'non-exterior edge'.format(node1, node2))
        boundary_id = _resolve_segment_boundary(
            boundary_by_id, label, (node1, node2), physical_nodes,
            'Flux {}-{}'.format(node1, node2))
        covered.add(edge)
        boundary = boundary_by_id[boundary_id]
        boundary_kinds[boundary_id].add('flux')
        edge_points = (physical_nodes[node1], physical_nodes[node2])
        boundary_segments[boundary_id].append(edge_points)
        if not all(_point_on_segment(point, *boundary['points'])
                   for point in edge_points):
            raise _contract('THMZ-E4003', 'Flux: boundary label {} does not '
                            'match the exterior edge geometry'
                            .format(boundary_id))
        used_boundaries.add(boundary_id)
        (record_film, _, record_flux, environment, _, view_factor, _humidity
         ) = condition_values[boundary['name']]
        if record_flux and not math.isclose(record_flux, flux,
                                            rel_tol=1e-9, abs_tol=1e-8):
            raise _contract('THMZ-E4005', 'Flux {}-{}: flux disagrees with '
                            'boundary condition {}'.format(
                                node1, node2, boundary['name']))
        if record_film != 0 or (environment != 0 and view_factor != 0):
            raise _contract('THMZ-E4005', 'Boundary {}: flux segments need an '
                            'inert boundary condition record'.format(
                                boundary['name']))
        if flux != 0:
            fluxes.append((node1, node2, flux))
        edge_bcs.append({'kind': 'flux', 'edge': edge,
                         'boundary_id': boundary_id, 'flux': flux})

    # Radiation segments carry no label; the boundary is resolved by geometry.
    for node1, node2, emissivity, radiant_temperature in segment_radiations:
        if (node1 == node2 or node1 < 0 or node2 < 0
                or node1 >= len(nodes) or node2 >= len(nodes)):
            raise _contract('THMZ-E4001', 'Radiation {}-{}: invalid node '
                            'indices'.format(node1, node2))
        edge = tuple(sorted((node1, node2)))
        if edges[edge] != 1 or edge in covered:
            raise _contract('THMZ-E4001', 'Radiation {}-{}: duplicate or '
                            'non-exterior edge'.format(node1, node2))
        edge_points = (physical_nodes[node1], physical_nodes[node2])
        candidates = [key for key, boundary in boundary_by_id.items()
                      if all(_point_on_segment(point, *boundary['points'])
                             for point in edge_points)]
        if len(candidates) != 1:
            raise _contract('THMZ-E4003', 'Radiation {}-{}: edge does not '
                            'match exactly one boundary'.format(node1, node2))
        boundary_id = candidates[0]
        covered.add(edge)
        boundary = boundary_by_id[boundary_id]
        boundary_kinds[boundary_id].add('radiation')
        boundary_segments[boundary_id].append(edge_points)
        used_boundaries.add(boundary_id)
        if boundary['name'] not in inert_names:
            raise _contract('THMZ-E4005', 'Boundary {}: radiation segments '
                            'need an inert boundary condition record'.format(
                                boundary['name']))
        radiations.append((node1, node2, emissivity, radiant_temperature))
        edge_bcs.append({'kind': 'radiation', 'edge': edge,
                         'boundary_id': boundary_id, 'exchange': emissivity,
                         'radiant_temperature': radiant_temperature})

    for boundary_id, kinds in boundary_kinds.items():
        # A boundary without any segment is reported by the coverage and
        # used-boundary checks below, not as a mixed-kind violation.
        if len(kinds) > 1:
            raise _contract('THMZ-E4005', 'Boundary {}: mixed boundary '
                            'segment kinds are unsupported'.format(
                                boundary_by_id[boundary_id]['name']))
    if covered != exterior:
        raise _contract('THMZ-E4001', 'Mesh.xml: every exterior edge needs an explicit BC')
    if used_boundaries != set(boundary_by_id):
        raise _contract('THMZ-E4002', 'Mesh.xml: every Model boundary needs an exterior mesh BC')

    return (convection, radiations, fluxes, fixed_temperatures,
            edge_bcs, boundary_segments)


def _series_values(entries, field, context):
    """Validate one timestep series and return it unexpanded.

    Entries may declare 1-based ``Index`` labels; THERM files routinely
    omit them or restart numbering, so the kernel binding applies the
    series cyclically with the entry count as the period (see contract
    section 9, unverified). The series stays compact here so memory does
    not scale with ``NumberOfTimesteps`` on the Python side.
    """
    if not entries:
        raise _contract('THMZ-E2003', '{}: timestep series is empty'.format(
            context))
    indices = [entry.get('index') for entry in entries]
    if any(index is not None for index in indices):
        if any(index is None for index in indices):
            raise _contract('THMZ-E2005', '{}: timestep Index must appear on '
                            'all or no entries'.format(context))
        entries = sorted(entries, key=lambda entry: entry['index'])
        if [entry['index'] for entry in entries] != list(
                range(1, len(entries) + 1)):
            raise _contract('THMZ-E2005', '{}: timestep Index values must be '
                            'contiguous from 1'.format(context))
    return tuple(entry[field] for entry in entries)


def _transient_boundary_conditions(members, roots, options, boundary_by_id,
                                   frame_cavity_boundaries, exterior,
                                   physical_nodes, nodes, condition_values,
                                   simulate_moisture=False):
    """Resolve transient-mode boundary conditions into per-step series.

    Transient archives drive thermal BCs from ``Boundary/TransientData``
    (TransientTypeBC record + timestep file) rather than Mesh.xml BC
    segments; the segments stay structurally validated inputs. Boundaries
    without TransientData must be thermally inert and moisture-sealed. A
    humidity value with zero film does not create moisture exchange. Edges
    are matched to boundaries geometrically (the label role of BCSegments
    has no transient counterpart; unverified, contract section 9).

    In hygrothermal solves (``simulate_moisture``) a Neumann record that
    declares a Convection model always carries the coupled humid Robin
    pair (air humidity from the convection timestep series or the
    SteadyState-style record scalar), matching THERM 8.1 behaviour.
    ``UseHumidity`` routes the pin BCs only: combined temperature+humidity
    pins or humidity-only pins. Convection declared on a pinned edge is
    inert metadata.
    """
    from .transient_input import validate_transient_inputs

    engine = options.engine_parameters
    engine_xml = roots['Model.xml'].find(
        'Properties/CalculationOptions/EngineParameters')
    time_step_text = (engine_xml.findtext('TimeStep')
                      if engine_xml is not None else None)
    try:
        time_step = _finite(float(time_step_text), 'EngineParameters TimeStep')
    except (TypeError, ValueError) as error:
        raise _contract('THMZ-E2004', 'Model.xml: TimeStep must be positive '
                        '(seconds)') from error
    if time_step <= 0:
        raise _contract('THMZ-E2004', 'Model.xml: TimeStep must be positive '
                        '(seconds)')
    num_steps_text = (engine_xml.findtext('NumberOfTimesteps')
                      if engine_xml is not None else None)
    try:
        num_steps = int(num_steps_text.strip())
    except (AttributeError, TypeError, ValueError) as error:
        raise _contract('THMZ-E2004', 'Model.xml: NumberOfTimesteps must be a '
                        'positive integer') from error
    if num_steps < 1:
        raise _contract('THMZ-E2004', 'Model.xml: NumberOfTimesteps must be a '
                        'positive integer')
    tolerance = _finite(engine.convergence_tolerance,
                        'EngineParameters ConvergenceTolerance')
    relaxation = _finite(engine.relaxation_parameter,
                         'EngineParameters RelaxationParameter')
    if tolerance <= 0 or not 0 < relaxation <= 1:
        raise _contract('THMZ-E2004', 'Model.xml: ConvergenceTolerance must '
                        'be positive and RelaxationParameter in (0, 1]')
    calc_opts_xml = roots['Model.xml'].find('Properties/CalculationOptions')
    methodology = (calc_opts_xml.findtext('TransientCalculationMethodology')
                   if calc_opts_xml is not None else None)
    if (methodology != 'Constant everywhere'
            or not isinstance(options.initial_conditions.state,
                              fem.UniformStart)):
        raise _contract('THMZ-E5016', 'Model.xml: only Constant everywhere '
                        'initial conditions are supported')
    init_xml = (calc_opts_xml.find('ConstantInitialConditionsTransient')
                if calc_opts_xml is not None else None)
    if init_xml is not None:
        initial_temperature = _xml_number(
            init_xml, 'Temperature',
            'ConstantInitialConditionsTransient Temperature')
        initial_humidity = _fraction(_xml_number(
            init_xml, 'Humidity',
            'ConstantInitialConditionsTransient Humidity'),
            'ConstantInitialConditionsTransient Humidity')
    else:
        initial = options.initial_conditions.state
        initial_temperature = _finite(
            initial.temperature,
            'ConstantInitialConditionsTransient Temperature')
        initial_humidity = _fraction(_finite(
            initial.humidity, 'ConstantInitialConditionsTransient Humidity'),
            'ConstantInitialConditionsTransient Humidity')

    references = validate_transient_inputs(members)
    record_by_boundary = {}
    for reference in references:
        boundary_id = reference['boundary_id']
        if boundary_id in record_by_boundary:
            raise _contract('THMZ-E2002', 'Boundary {}: duplicate '
                            'TransientData'.format(boundary_id))
        record_by_boundary[boundary_id] = reference
    frame_ids = {boundary.findtext('ID')
                 for boundary, _ in frame_cavity_boundaries}
    for boundary_id in record_by_boundary:
        if boundary_id in frame_ids:
            raise _contract('THMZ-E4005', 'Frame Cavity boundary {} cannot '
                            'carry TransientData'.format(boundary_id))

    # Geometric edge->boundary assignment, ordered along the boundary line
    # so the result edge entity ids are stable.
    edges_by_boundary = {}
    for edge in sorted(exterior):
        points = (physical_nodes[edge[0]], physical_nodes[edge[1]])
        candidates = [key for key, boundary in boundary_by_id.items()
                      if all(_point_on_segment(point, *boundary['points'])
                             for point in points)]
        if len(candidates) != 1:
            raise _contract('THMZ-E4003', 'Mesh.xml: exterior edge {} does '
                            'not match exactly one boundary'.format(edge))
        boundary_id = candidates[0]
        boundary = boundary_by_id[boundary_id]
        origin, endpoint = boundary['points']
        axis = (endpoint[0] - origin[0], endpoint[1] - origin[1])
        midpoint = ((points[0][0] + points[1][0]) / 2 - origin[0],
                    (points[0][1] + points[1][1]) / 2 - origin[1])
        projection = midpoint[0] * axis[0] + midpoint[1] * axis[1]
        edges_by_boundary.setdefault(boundary_id, []).append(
            (projection, edge))
    for boundary_id, edges in edges_by_boundary.items():
        edges_by_boundary[boundary_id] = [
            edge for _, edge in sorted(edges)]
    if edges_by_boundary.keys() != boundary_by_id.keys():
        missing = set(boundary_by_id) - set(edges_by_boundary)
        raise _contract('THMZ-E4002', 'Boundary {}: no exterior mesh edge '
                        'lies on the boundary'.format(sorted(missing)[0]))

    ts_convection, ts_temperatures, ts_fluxes = [], [], []
    ts_radiations, ts_linearized = [], []
    ts_humid_convection, ts_humidities, ts_temperature_humidities = \
        [], [], []
    boundary_segments = {key: [] for key in boundary_by_id}
    boundary_edges = []
    anchored = False

    for boundary_id in sorted(
            edges_by_boundary,
            key=lambda value: (0, int(value)) if str(value).isdigit()
            else (1, str(value))):
        boundary = boundary_by_id[boundary_id]
        edges = edges_by_boundary[boundary_id]
        boundary_edges.extend(edges)
        for edge in edges:
            boundary_segments[boundary_id].append(
                (physical_nodes[edge[0]], physical_nodes[edge[1]]))
        reference = record_by_boundary.get(boundary_id)
        context = 'Boundary {}'.format(boundary['name'])
        if reference is None:
            # Do not synthesize constant transient BCs for unreferenced active boundaries.
            (film, temperature, flux, environment, radiant, view,
             humidity) = condition_values[boundary['name']]
            if film < 0:
                raise _contract('THMZ-E2004', '{}: film coefficient must be '
                                'non-negative'.format(context))
            if (film != 0 or flux != 0 or
                    (boundary['emissivity'] != 0 and environment != 0
                     and view != 0)):
                # Report source fields verbatim, not a derived exchange factor.
                steady_record = next(
                    record for record in ET.fromstring(
                        members['SteadyStateBC.xml']).findall(
                            'BoundaryCondition')
                    if record.findtext('Name') == boundary['name'])
                active_fields = []
                if film != 0:
                    path = ('Simplified/FilmCoefficient'
                            if steady_record.find('Simplified') is not None
                            else 'Comprehensive/Convection/FilmCoefficient')
                    active_fields.append('SteadyStateBC.xml/{}={!r}'.format(
                        path, steady_record.findtext(path)))
                if flux != 0:
                    path = 'Comprehensive/ConstantFlux/Flux'
                    active_fields.append('SteadyStateBC.xml/{}={!r}'.format(
                        path, steady_record.findtext(path)))
                if (boundary['emissivity'] != 0 and environment != 0
                        and view != 0):
                    model_boundary = next(
                        record for record in ET.fromstring(
                            members['Model.xml']).findall('Boundaries/Boundary')
                        if record.findtext('ID') == str(boundary_id))
                    path = 'ThermalEmissionProperties/Emissivity'
                    active_fields.append('Model.xml/{}={!r}'.format(
                        path, model_boundary.findtext(path)))
                    for field in ('Emissivity', 'ViewFactor'):
                        path = ('Comprehensive/Radiation/BlackBodyRadiation/'
                                + field)
                        active_fields.append(
                            'SteadyStateBC.xml/{}={!r}'.format(
                                path, steady_record.findtext(path)))
                raise _contract(
                    TRANSIENT_BOUNDARY_WITHOUT_DATA,
                    '{} (ID {}): non-adiabatic boundary '
                    'requires explicit TransientData in Transient mode; '
                    'SteadyStateBC constant fallback is unsupported; '
                    'active source fields: {}'.format(
                        context, boundary_id, ', '.join(active_fields)))
            continue

        record = reference['record']
        timestep_file = reference['timestep_file']
        transient_series = record['bc_type'] == 'Transient'
        convection = record.get('convection')
        radiation = record.get('radiation')
        solar = record.get('solar')
        if record['use_humidity'] and not simulate_moisture:
            raise _contract('THMZ-E5003', '{}: humidity boundary conditions '
                            'are unsupported in dry solves'.format(context))
        # Pins dominate: a UseHumidity edge that pins humidity (with
        # UseTemperature, or on any Dirichlet-model record) routes to the
        # pin BCs and leaves convection/radiation/flux/solar declarations
        # inert metadata, so their models and timestep series are neither
        # required nor validated against the kernel's bound subset
        # (contract section 5).
        pinned = (simulate_moisture and record['use_humidity'] and
                  (record['use_temperature'] or
                   record['bc_model'] == 'Dirichlet'))
        if solar is not None and not pinned:
            solar_active = any(
                solar.get(key) not in (None, 0, 0.0)
                for key in ('solar_radiation', 'absorptance')) or (
                    transient_series and timestep_file.solar_radiation)
            if solar_active:
                raise _contract('THMZ-E5016', '{}: solar boundary conditions '
                                'are unsupported'.format(context))

        convection_series = None
        if convection is not None and not pinned:
            model_name = convection['model']
            if model_name != 'Fixed Convection Coefficient':
                raise _contract('THMZ-E5016', '{}: transient convection '
                                'model {} is not bound to the kernel'
                                .format(context, model_name))
            if transient_series:
                entries = timestep_file.convection.get(
                    'FixedConvectionFilmTimestep')
                film_series = _series_values(
                    entries, 'film_coefficient',
                    context + ' FixedConvectionFilmTimestep')
                temperature_series = _series_values(
                    entries, 'temperature',
                    context + ' FixedConvectionFilmTimestep')
            else:
                film = convection.get('film_coefficient')
                temperature = convection.get('temperature')
                if film is None or temperature is None:
                    raise _contract('THMZ-E2003', '{}: steady transient '
                                    'record requires Convection '
                                    'FilmCoefficient and Temperature'
                                    .format(context))
                film_series = (film,)
                temperature_series = (temperature,)
            if min(film_series) < 0:
                raise _contract('THMZ-E2004', '{}: film coefficients must '
                                'be non-negative'.format(context))
            convection_series = (film_series, temperature_series)

        radiation_kind = None
        if radiation is not None and not pinned:
            model_name = radiation['model']
            if model_name == 'Automatic Enclosure':
                raise _contract('THMZ-E5016', '{}: transient enclosure '
                                'radiation is unsupported'.format(context))
            if model_name == 'Fixed Radiation Coefficient':
                if transient_series:
                    entries = timestep_file.radiation.get(
                        'FixedRadiationCoefficientTimestep')
                    hr_series = _series_values(
                        entries, 'hr',
                        context + ' FixedRadiationCoefficientTimestep')
                    temperature_series = _series_values(
                        entries, 'temperature',
                        context + ' FixedRadiationCoefficientTimestep')
                else:
                    hr = radiation.get('hr')
                    temperature = radiation.get('temperature')
                    if hr is None or temperature is None:
                        raise _contract('THMZ-E2003', '{}: steady transient '
                                        'record requires Radiation hr and '
                                        'Temperature'.format(context))
                    hr_series = (hr,)
                    temperature_series = (temperature,)
                if min(hr_series) < 0:
                    raise _contract('THMZ-E2004', '{}: radiation hr must be '
                                    'non-negative'.format(context))
                radiation_kind = ('linearized', hr_series, temperature_series)
            else:  # Black Body Radiation
                if transient_series:
                    entries = timestep_file.radiation.get(
                        'BlackBodyRadiationTimestep')
                    emissivity_series = _series_values(
                        entries, 'emissivity',
                        context + ' BlackBodyRadiationTimestep')
                    temperature_series = _series_values(
                        entries, 'temperature',
                        context + ' BlackBodyRadiationTimestep')
                else:
                    emissivity = radiation.get('surface_emissivity',
                                               boundary['emissivity'])
                    temperature = radiation.get('temperature')
                    if temperature is None:
                        raise _contract('THMZ-E2003', '{}: steady transient '
                                        'record requires Radiation '
                                        'Temperature'.format(context))
                    emissivity_series = (emissivity,)
                    temperature_series = (temperature,)
                view = radiation.get('view_factor')
                if view not in (None, 1.0):
                    emissivity_series = [
                        emissivity * view for emissivity in
                        emissivity_series]
                radiation_kind = ('blackbody', emissivity_series,
                                  temperature_series)

        flux_series = None
        if record['use_heat_flux'] and not pinned:
            if transient_series:
                flux_series = _series_values(
                    timestep_file.heat_flux, 'heat_flux',
                    context + ' HeatFluxTimestep')
            else:
                flux = record.get('heat_flux')
                if flux is None:
                    raise _contract('THMZ-E2003', '{}: steady transient '
                                    'record requires HeatFlux'
                                    .format(context))
                flux_series = (flux,)

        temperature_bc_series = None
        if record['use_temperature']:
            if transient_series:
                temperature_bc_series = _series_values(
                    timestep_file.temperature, 'temperature',
                    context + ' TemperatureTimestep')
            else:
                temperature = record.get('temperature')
                if temperature is None:
                    raise _contract('THMZ-E2003', '{}: steady transient '
                                    'record requires Temperature'
                                    .format(context))
                temperature_bc_series = (temperature,)

        humidity_series = None
        humidity_style = None
        if simulate_moisture:
            # Pins dominate: UseTemperature+UseHumidity pins both state
            # variables regardless of bcModel; UseHumidity alone pins
            # humidity on Dirichlet-style boundaries even when a Convection
            # sub-record is declared (it stays inert metadata). On Neumann
            # records that declare a Convection model the edge always
            # carries the moisture Robin pair, whether UseHumidity is set
            # or not (matching THERM 8.1 behaviour); the flag
            # only routes pins, it is not the exchange switch.
            if record['use_humidity'] and \
                    temperature_bc_series is not None:
                humidity_style = 'temperature_humidity'
            elif record['use_humidity'] and \
                    record['bc_model'] == 'Dirichlet':
                humidity_style = 'humidity'
            elif record['bc_model'] == 'Neumann' and \
                    convection_series is not None:
                humidity_style = 'convection'
            elif record['use_humidity']:
                raise _contract('THMZ-E5016', '{}: humidity exchange '
                                'requires a Convection model (UseHumidity '
                                'with bcModel Neumann)'.format(context))
            if humidity_style == 'convection':
                # The air humidity rides the convection timestep series
                # (FixedConvectionFilmTimestep Humidity column).
                if transient_series:
                    entries = timestep_file.convection.get(
                        'FixedConvectionFilmTimestep')
                    humidity_series = _series_values(
                        entries, 'humidity',
                        context + ' FixedConvectionFilmTimestep')
                else:
                    humidity = record.get('humidity')
                    if humidity is None:
                        raise _contract('THMZ-E2003', '{}: steady '
                                        'transient record requires '
                                        'Humidity'.format(context))
                    humidity_series = (humidity,)
            elif humidity_style is not None and transient_series:
                humidity_series = _series_values(
                    timestep_file.humidity, 'humidity',
                    context + ' HumidityTimestep')
            elif humidity_style is not None:
                humidity = record.get('humidity')
                if humidity is None:
                    raise _contract('THMZ-E2003', '{}: steady transient '
                                    'record requires Humidity'
                                    .format(context))
                humidity_series = (humidity,)

        for edge in edges:
            # Moisture-pinned edges keep convection, radiation and heat
            # flux declarations as inert metadata (contract section 9):
            # the kernel pair createBC_FixedTemperatureAndHumidity /
            # moisture FixedHumidity owns the edge completely.
            if humidity_style == 'temperature_humidity':
                ts_temperature_humidities.append(
                    (edge[0], edge[1], temperature_bc_series,
                     humidity_series))
                anchored = True
                continue
            if humidity_style == 'humidity':
                ts_humidities.append((edge[0], edge[1], humidity_series))
                continue
            if humidity_style == 'convection':
                ts_humid_convection.append(
                    (edge[0], edge[1]) + convection_series
                    + (humidity_series,))
                if max(convection_series[0]) > 0:
                    anchored = True
            elif convection_series is not None:
                ts_convection.append(
                    (edge[0], edge[1]) + convection_series)
                if max(convection_series[0]) > 0:
                    anchored = True
            if radiation_kind is not None:
                kind, first, second = radiation_kind
                if kind == 'blackbody':
                    ts_radiations.append((edge[0], edge[1], first, second))
                    if max(first) > 0:
                        anchored = True
                else:
                    ts_linearized.append((edge[0], edge[1], first, second))
                    if max(first) > 0:
                        anchored = True
            if flux_series is not None:
                ts_fluxes.append((edge[0], edge[1], flux_series))
            if temperature_bc_series is not None:
                ts_temperatures.append(
                    (edge[0], edge[1], temperature_bc_series))
                anchored = True

    return {
        'time_step': time_step,
        'num_steps': num_steps,
        'convergence_tolerance': tolerance,
        'relaxation': relaxation,
        'initial_temperature': initial_temperature,
        'initial_humidity': initial_humidity,
        'convection': ts_convection,
        'humid_convection': ts_humid_convection,
        'temperatures': ts_temperatures,
        'humidities': ts_humidities,
        'temperature_humidities': ts_temperature_humidities,
        'fluxes': ts_fluxes,
        'radiations': ts_radiations,
        'linearized_radiations': ts_linearized,
        'edge_order': boundary_edges,
        'boundary_segments': boundary_segments,
        'anchored': anchored,
        'hygrothermal': simulate_moisture,
    }


def _results(case, temperatures, fluxes):
    if len(temperatures) != len(case.nodes) or len(fluxes) != len(case.nodes):
        raise SolveError('Solver returned an incomplete node result set')
    records = []
    for node, temperature, flux in zip(case.nodes, temperatures, fluxes):
        record = fem.NodeResults()
        record.index = node.index
        record.temperature = _finite(temperature, 'Result temperature')
        record.x_flux = _finite(flux[0], 'Result x-flux')
        record.y_flux = _finite(flux[1], 'Result y-flux')
        records.append(record)
    result_case = fem.CaseMeshResults()
    result_case.glazing_case = case.glazing_case
    result_case.spacer_case = case.spacer_case
    result_case.nodes = records
    result = fem.MeshResults()
    result.cases = [result_case]
    return fem.steady_state_mesh_results.to_string(result)


def _radiation_outward(t1, t2, exchange, radiant_temperature):
    """Outward radiative flux (W/m2) using the kernel's two-Gauss rule."""
    mean = (t1 + t2) / 2 + 273.15
    offset = (t2 - t1) / (2 * math.sqrt(3))
    return exchange * STEFAN_BOLTZMANN * (
        ((mean - offset) ** 4 + (mean + offset) ** 4) / 2 -
        (radiant_temperature + 273.15) ** 4)


def _edge_conduction_outward(directed, nodes, quads, fluxes):
    """Outward conducted heat rate (W/m) through an exterior edge.

    ``directed`` is the owning element's edge orientation (u, v); the outward
    normal of a counter-clockwise Q4 edge u -> v is (dy, -dx) / L.
    """
    u, v, _ = directed
    x1, y1 = nodes[u][1], nodes[u][2]
    x2, y2 = nodes[v][1], nodes[v][2]
    length = math.dist((x1, y1), (x2, y2))
    normal = ((y2 - y1) / length, -(x2 - x1) / length)
    q1, q2 = fluxes[u], fluxes[v]
    mean_x, mean_y = (q1[0] + q2[0]) / 2, (q1[1] + q2[1]) / 2
    return length * (mean_x * normal[0] + mean_y * normal[1])


def _edge_outward_rates(edge_bcs, nodes, quads, fluxes, temperatures):
    """Outward integrated heat rate (W/m depth) per boundary edge.

    One ``(edge, rate)`` entry per ``edge_bcs`` record, in the same order;
    ``edge`` is the stored unordered ``(min, max)`` node-position pair.
    Convection integrates exactly, radiation uses the kernel's Gauss rule,
    applied flux is its prescribed outward value, and fixed-temperature
    edges use the element-side conduction integral. Use unrounded
    temperatures, never smoothed display fluxes; mesh lengths are m.
    """
    rates = []
    for bc in edge_bcs:
        first, second = bc['edge']
        a, b = nodes[first][1:], nodes[second][1:]
        length = math.dist(a, b)
        t1, t2 = temperatures[first], temperatures[second]
        if bc['kind'] == 'convection':
            outward = bc['h'] * ((t1 + t2) / 2 - bc['air_temperature']) \
                - bc['flux']
            if bc['exchange']:
                outward += _radiation_outward(
                    t1, t2, bc['exchange'], bc['radiant_temperature'])
        elif bc['kind'] == 'flux':
            outward = -bc['flux']
        elif bc['kind'] == 'radiation':
            outward = _radiation_outward(
                t1, t2, bc['exchange'], bc['radiant_temperature'])
        else:  # 'temperature'
            outward = _edge_conduction_outward(
                bc['directed'], nodes, quads, fluxes) / length
        rates.append((bc['edge'], length * outward))
    return rates


def _u_factor_results(model, case, temperatures, edge_bcs, quads, nodes,
                      fluxes):
    """Integrate outward boundary heat (W/m depth) over each FluxTag.

    Per-edge rates come from ``_edge_outward_rates``; fixed-temperature
    edges use the element-side conduction integral (the kernel's huge-film
    pin cannot be reintegrated safely). Model lengths and result lengths
    are mm; mesh lengths are m.
    """
    boundaries = {int(b.findtext('ID')): b
                  for b in model.findall('Boundaries/Boundary')}
    groups = {}
    for boundary_id, boundary in boundaries.items():
        tag = boundary.findtext('FluxTag')
        if tag:
            groups.setdefault(tag, []).append(boundary_id)
    heat = {boundary_id: [] for boundary_id in boundaries}
    ambient = []
    rates = _edge_outward_rates(edge_bcs, nodes, quads, fluxes, temperatures)
    for bc, (_edge, rate) in zip(edge_bcs, rates):
        if bc['kind'] == 'convection':
            if bc['h'] > 0:
                ambient.append(bc['air_temperature'])
        elif bc['kind'] == 'radiation':
            ambient.append(bc['radiant_temperature'])
        elif bc['kind'] == 'temperature':
            ambient.append(bc['temperature'])
        heat[int(bc['boundary_id'])].append(rate)
    if not ambient:
        ambient = [0.0]
    delta = _finite(max(ambient) - min(ambient), 'U-factor DeltaT')
    records = []
    for tag, ids in groups.items():
        record = fem.SteadyStateUFactors()
        record.tag = tag
        record.delta_t = delta
        record.heat_flux = _finite(math.fsum(
            value for boundary_id in ids for value in heat[boundary_id]),
            'U-factor HeatFlux')
        record.default_display_type = fem.UValueDimensionType.TotalLength
        segments = [tuple((float(boundaries[i].findtext(point + '/x')),
                           float(boundaries[i].findtext(point + '/y')))
                          for point in ('StartPoint', 'EndPoint')) for i in ids]
        lengths = [math.fsum(math.dist(a, b) for a, b in segments)]
        for axis in (0, 1):
            # Union projected intervals: folds/overlaps count once, gaps do not.
            end, length = -math.inf, 0.0
            for low, high in sorted(sorted((a[axis], b[axis]))
                                    for a, b in segments):
                length += max(0.0, high - max(low, end))
                end = max(end, high)
            lengths.append(length)
        projections = []
        for kind, length in zip((fem.UValueDimensionType.TotalLength,
                                 fem.UValueDimensionType.XProjected,
                                 fem.UValueDimensionType.YProjected), lengths):
            projection = fem.Projection()
            projection.length_type = kind
            projection.length = _finite(length, 'U-factor length')
            if length > 0 and delta > 0:
                projection.u_factor = _finite(
                    abs(record.heat_flux) / (length / 1000) / delta,
                    'U-factor')
            projections.append(projection)
        # Glass/custom angles cannot be inferred from a plain solid model.
        record.projections = projections
        records.append(record)
    result_case = fem.SteadyStateResultsCase()
    result_case.model_type = fem.RunType.UFactor
    result_case.steady_state_u_factors = records
    result = fem.SteadyStateResults()
    result.cases = [result_case]
    return fem.steady_state_results.to_string(result)


def _solve_members(members, roots, input_digest, result_layout='native'):
    """Validate inputs, run the kernel, and assemble the result handle."""
    (case, nodes, quads, materials, convection, radiations,
     added_fluxes, fixed_temperatures, edge_bcs, gravity,
     cavity_surface_emissivities, cavity_model_mappings,
     transient_mode, transient_material_props, transient_context,
     geometry_context, simulate_moisture, physics,
     moisture_material_props) = _inputs(members, roots)
    if transient_mode:
        return _solve_transient_members(
            members, roots, input_digest, case, nodes, quads, materials,
            gravity, cavity_surface_emissivities, cavity_model_mappings,
            transient_material_props, transient_context, geometry_context,
            physics, moisture_material_props, result_layout)
    if result_layout == 'therm':
        raise _contract('THMZ-E2005', "result_layout='therm': requires "
                        "CalculationMode='Transient'; received 'Steady-State'")
    check_error = roots['Model.xml'].findtext(
        'Properties/CalculationOptions/MeshControl/RunErrorEstimator')
    if check_error not in ('true', 'false'):
        raise _contract('THMZ-E2005', 'Model.xml: RunErrorEstimator must be true or false')
    verified_kernel_commit()
    from . import _native
    try:
        temperatures, fluxes, energy_error = _native.solve_steady(
            nodes, quads, materials, convection, radiations=radiations,
            fluxes=added_fluxes, temperatures=fixed_temperatures,
            gravity=gravity,
            estimate_error=check_error == 'true',
            cavity_surface_emissivities=cavity_surface_emissivities)
    except (RuntimeError, ValueError) as error:
        raise SolveError('{}'.format(error)) from error
    expected_tags = set()
    for boundary in roots['Model.xml'].findall('Boundaries/Boundary'):
        tag = boundary.findtext('FluxTag')
        if tag:
            expected_tags.add(tag)

    def build_results():
        try:
            result_xml = _results(case, temperatures, fluxes)
            u_factor_xml = _u_factor_results(
                roots['Model.xml'], case, temperatures, edge_bcs, quads,
                nodes, fluxes)
        except ContractError as error:
            raise SolveError(str(error.args[0])) from error
        return result_xml, u_factor_xml

    kernel_commit = verified_kernel_commit()
    provenance = {
        'contract_version': CONTRACT_VERSION,
        'solver_version': SOLVER_VERSION,
        'input_sha256': input_digest,
        'package': 'pyHygroThermFEM-Fairyfly',
        'pyhygrothermfem_fairyfly': _package_version(),
        'libraryfemtherm': version('libraryfemtherm'),
        'kernel_commit': kernel_commit,
        'mode': 'dry-steady',
        'cavity_model_mappings': cavity_model_mappings,
        'energy_error_percent': energy_error if check_error == 'true' else None,
        'energy_error_method': ('HygroThermFEM recovery energy norm'
                                if check_error == 'true' else None),
    }
    passthrough = {
        name: content for name, content in members.items()
        if (name not in RESULT_MEMBERS
            and not name.replace('\\', '/').startswith('transient results/'))}
    return SolvedResult(
        'dry-steady', tuple(temperatures), tuple(map(tuple, fluxes)),
        energy_error if check_error == 'true' else None,
        provenance, passthrough, build_results,
        (nodes, case, expected_tags, edge_bcs, quads))


def _transient_geometry(roots, case, nodes, quads, geometry_context):
    """Build the transient results/Geometry.xml payload dict.

    Node IDs are the Mesh.xml node labels; element and material IDs are the
    Mesh.xml labels; material polygons carry the Model.xml polygon ID with
    corner points snapped to their mesh nodes (unverified, contract 9).
    """
    polygon_geometries = geometry_context['polygon_geometries']
    uuid_by_material_id = geometry_context['uuid_by_material_id']
    model = roots['Model.xml']
    node_label_by_position = [node.index for node in case.nodes]
    point_by_position = {i: (node.x, node.y) for i, node in
                         enumerate(case.nodes)}
    # Model-space points (mm) per node position for polygon corner matching.
    glazing_origin = model.find('GlazingOrigin')
    origin_x = _xml_number(glazing_origin, 'x', 'GlazingOrigin x')
    origin_y = _xml_number(glazing_origin, 'y', 'GlazingOrigin y')
    physical = {i: (node.x * 1000 + origin_x, node.y * 1000 + origin_y)
                for i, node in enumerate(case.nodes)}

    material_names = {}
    material_colors = {}
    for record in roots['Materials.xml'].findall('Material'):
        material_names[(record.findtext('UUID') or '').casefold()] = \
            record.findtext('Name') or ''
        material_colors[(record.findtext('UUID') or '').casefold()] = \
            record.findtext('Color') or ''
    materials = []
    for material_id in sorted(uuid_by_material_id):
        uuid = uuid_by_material_id[material_id]
        materials.append({'id': material_id,
                          'name': material_names.get(uuid, ''),
                          'color': material_colors.get(uuid, '')})

    polygon_xmls = model.findall('Polygons/Polygon')
    material_polygons = []
    for sequence, (polygon, polygon_xml) in enumerate(
            zip(polygon_geometries, polygon_xmls), start=1):
        id_text = polygon_xml.findtext('ID')
        try:
            polygon_id = int(id_text) if id_text else sequence
        except ValueError:
            polygon_id = sequence
        corner_ids = []
        for point in polygon['points']:
            candidates = [position for position, xy in physical.items()
                          if math.dist(xy, point) <= BOUNDARY_TOLERANCE_MM]
            if candidates:
                position = candidates[0]
            else:
                # UNVERIFIED (contract 9): snap unmatched polygon corners to
                # the nearest mesh node rather than dropping geometry.
                position = min(physical,
                               key=lambda item: math.dist(physical[item],
                                                          point))
            corner_ids.append(node_label_by_position[position])
        material_polygons.append({
            'id': polygon_id, 'material_id': polygon['material_id'],
            'node_ids': corner_ids})

    # The model enclosure is the ordered exterior perimeter (0-based
    # positions translated to node labels).
    exterior = {}
    edges_count = Counter()
    for quad in quads:
        for i in range(4):
            pair = tuple(sorted((quad[i], quad[(i + 1) % 4])))
            edges_count[pair] += 1
    for first, second in (e for e, c in edges_count.items() if c == 1):
        exterior.setdefault(first, []).append(second)
        exterior.setdefault(second, []).append(first)
    enclosure = []
    start = min(exterior) if exterior else None
    if start is not None:
        current, previous = start, None
        while True:
            enclosure.append(node_label_by_position[current])
            candidates = [n for n in exterior[current] if n != previous]
            if not candidates:
                break
            previous, current = current, candidates[0]
            if current == start:
                break
    return {
        'materials': materials,
        'nodes': [{'id': node_label_by_position[i], 'x': x, 'y': y}
                  for i, (x, y) in point_by_position.items()],
        'elements': [{'id': element.index,
                      'node_ids': [node_label_by_position[n] for n in quad],
                      'material_id': element.material_id}
                     for element, quad in zip(case.elements, quads)],
        'material_polygons': material_polygons,
        'model_enclosure': enclosure,
    }


def _solve_transient_members(members, roots, input_digest, case, nodes,
                             quads, materials, gravity,
                             cavity_surface_emissivities,
                             cavity_model_mappings,
                             transient_material_props, context,
                             geometry_context, physics=None,
                             moisture_material_props=None,
                             result_layout='native'):
    """Run the transient dispatch path and stream steps into the result."""
    from contextlib import ExitStack
    from . import transient_results as series_io
    verified_kernel_commit()
    from . import _native

    hygrothermal = context.get('hygrothermal', False)

    densities = []
    heat_capacities = []
    hygro_materials = []
    for material in materials:
        if hygrothermal:
            # Solids carry the parsed HygroThermal record; gas cavity
            # materials map to None (no moisture extension).
            hygro_materials.append(
                (moisture_material_props or {}).get(material.region_key))
        else:
            props = transient_material_props.get(material.region_key)
            densities.append(props[0] if props else 0.0)
            heat_capacities.append(props[1] if props else 0.0)

    node_ids = [node.index for node in case.nodes]
    edge_ids = list(range(1, len(context['edge_order']) + 1))
    edge_columns = {edge: entity for entity, edge in
                    zip(edge_ids, context['edge_order'])}

    temp_dir = tempfile.TemporaryDirectory(
        prefix='.pyhygrothermfem-transient-')
    writer_files = ExitStack()
    try:
        directory = Path(temp_dir.name)
        result_members = (series_io.THERM_TRANSIENT_RESULT_MEMBERS
                          if result_layout == 'therm'
                          else dict(series_io.TRANSIENT_RESULT_MEMBERS,
                                    **series_io.TRANSIENT_STEP_EXCHANGE_MEMBERS))
        member_paths = {
            name: directory / name.replace('\\', '/').split('/')[-1]
            for name in result_members.values()}
        writers = {}
        for key, member in result_members.items():
            if key == 'geometry':
                continue
            stream = writer_files.enter_context(member_paths[member].open(
                'w', encoding='utf-8', newline=''))
            if result_layout == 'therm':
                kind = ('edges' if key.endswith('_edges') else
                        'vector' if key in ('heat_flux', 'water_flux')
                        else 'scalar')
                writers[key] = series_io.ThermTransientSeriesWriter(
                    stream, () if kind == 'edges' else node_ids,
                    kind, vector_convention='geometry-xy-signed'
                    if kind == 'vector' else None, member=member)
            else:
                writers[key] = series_io.TransientSeriesWriter(
                    stream, edge_ids
                    if key.endswith('_edges') or
                    key.endswith('_step_exchange')
                    else node_ids)
        completed_frames = 0

        def on_step(frame):
            (step_index, time, temperature, humidity, water_content,
             _ice_content, heat_flux, water_flux, edge_rates,
             edge_water_rates, edge_heat_exchange, edge_water_exchange,
             temperature_error, humidity_error) = frame
            nonlocal completed_frames
            if result_layout == 'therm':
                if step_index == -1 and time == 0 and completed_frames == 0:
                    return
                if (step_index != completed_frames or
                        time != (step_index + 1) * context['time_step']):
                    raise SolveError('Transient frame step/time: received '
                                     '{!r}/{!r}, expected {!r}/{!r}'.format(
                                         step_index, time, completed_frames,
                                         (completed_frames + 1)
                                         * context['time_step']))
                writers['temperatures'].write_step(
                    time, temperature, temperature_error)
                writers['humidities'].write_step(time, humidity, humidity_error)
                writers['water_content'].write_step(
                    time, water_content, humidity_error)
                writers['heat_flux'].write_step(time, heat_flux)
                writers['water_flux'].write_step(time, water_flux)
                writers['heat_flux_edges'].write_step(time)
                writers['water_flux_edges'].write_step(time)
                completed_frames += 1
                return
            writers['temperatures'].write_step(time, temperature)
            writers['humidities'].write_step(time, humidity)
            writers['water_content'].write_step(time, water_content)
            writers['heat_flux'].write_step(
                time, [math.hypot(x, y) for x, y in heat_flux])
            rates = {}
            for a, b, rate in edge_rates:
                rates.setdefault(tuple(sorted((a, b))), []).append(rate)
            writers['heat_flux_edges'].write_step(
                time, [math.fsum(rates.get(edge, ()))
                       for edge in context['edge_order']])
            writers['water_flux'].write_step(
                time, [math.hypot(x, y) for x, y in water_flux])
            water_rates = {}
            for a, b, rate in edge_water_rates:
                water_rates.setdefault(tuple(sorted((a, b))), []).append(
                    rate)
            writers['water_flux_edges'].write_step(
                time, [math.fsum(water_rates.get(edge, ()))
                       for edge in context['edge_order']])
            # Interval exchange (J/m, kg/m) booked by the kernel accumulators
            # over the accepted sub-steps ending at this frame. The t=0 frame
            # carries no interval and writes zeros.
            exchanges = {}
            for a, b, exchange in edge_heat_exchange:
                exchanges.setdefault(tuple(sorted((a, b))), []).append(
                    exchange)
            water_exchanges = {}
            for a, b, exchange in edge_water_exchange:
                water_exchanges.setdefault(tuple(sorted((a, b))), []).append(
                    exchange)
            writers['heat_flux_step_exchange'].write_step(
                time, [math.fsum(exchanges.get(edge, ()))
                       for edge in context['edge_order']])
            writers['water_flux_step_exchange'].write_step(
                time, [math.fsum(water_exchanges.get(edge, ()))
                       for edge in context['edge_order']])

        try:
            if hygrothermal:
                (temperatures, fluxes, _humidities, _water_fluxes,
                 steps, _bc_slots) = _native.solve_hygrothermal(
                    nodes, quads, materials, hygro_materials, physics,
                    convection=context['convection'],
                    humid_convection=context['humid_convection'],
                    temperatures=context['temperatures'],
                    humidities=context['humidities'],
                    temperature_humidities=
                    context['temperature_humidities'],
                    fluxes=context['fluxes'],
                    radiations=context['radiations'],
                    linearized_radiations=
                    context['linearized_radiations'],
                    initial_temperature=context['initial_temperature'],
                    initial_humidity=context['initial_humidity'],
                    time_step=context['time_step'],
                    num_steps=context['num_steps'],
                    convergence_tolerance=context['convergence_tolerance'],
                    relaxation=context['relaxation'],
                    gravity=gravity,
                    cavity_surface_emissivities=
                    cavity_surface_emissivities,
                    on_step=on_step)
            else:
                (temperatures, fluxes, steps,
                 _bc_slots) = _native.solve_transient(
                    nodes, quads, materials, densities, heat_capacities,
                    convection=context['convection'],
                    temperatures=context['temperatures'],
                    fluxes=context['fluxes'],
                    radiations=context['radiations'],
                    linearized_radiations=context['linearized_radiations'],
                    initial_temperature=context['initial_temperature'],
                    initial_humidity=context['initial_humidity'],
                    time_step=context['time_step'],
                    num_steps=context['num_steps'],
                    convergence_tolerance=context['convergence_tolerance'],
                    relaxation=context['relaxation'],
                    gravity=gravity,
                    cavity_surface_emissivities=cavity_surface_emissivities,
                    on_step=on_step)
        except (RuntimeError, ValueError) as error:
            raise SolveError('{}'.format(error)) from error
        finally:
            try:
                for writer in writers.values():
                    writer.close()
            finally:
                writer_files.close()
        if steps != context['num_steps']:
            raise SolveError('Transient solve returned {} of {} steps'.format(
                steps, context['num_steps']))
        if result_layout == 'therm' and completed_frames != steps:
            raise SolveError('Transient callback frames {!r}, expected {!r}'
                             .format(completed_frames, steps))
        geometry = _transient_geometry(roots, case, nodes, quads,
                                       geometry_context)
        geometry_path = member_paths[result_members['geometry']]
        geometry_xml = series_io.geometry_to_xml(geometry)
        if result_layout == 'therm':
            geometry_root = ET.fromstring(geometry_xml)
            geometry_root.find('Version').text = None
            geometry_xml = ET.tostring(geometry_root, encoding='unicode')
        geometry_path.write_text(
            geometry_xml, encoding='utf-8')
        kernel_commit = verified_kernel_commit()
    except Exception:
        try:
            writer_files.close()
        finally:
            temp_dir.cleanup()
        raise

    provenance = {
        'contract_version': CONTRACT_VERSION,
        'solver_version': SOLVER_VERSION,
        'input_sha256': input_digest,
        'package': 'pyHygroThermFEM-Fairyfly',
        'pyhygrothermfem_fairyfly': _package_version(),
        'libraryfemtherm': version('libraryfemtherm'),
        'kernel_commit': kernel_commit,
        'mode': 'hygrothermal-transient' if hygrothermal else
                'dry-transient',
        'result_layout': result_layout,
        'cavity_model_mappings': cavity_model_mappings,
        'time_step': context['time_step'],
        'number_of_timesteps': context['num_steps'],
        'energy_error_percent': None,
        'energy_error_method': None,
    }
    passthrough = {
        name: content for name, content in members.items()
        if (name not in RESULT_MEMBERS
            and not name.replace('\\', '/').startswith('transient results/'))}
    return SolvedResult(
        'hygrothermal-transient' if hygrothermal else 'dry-transient',
        tuple(temperatures), tuple(map(tuple, fluxes)),
        None, provenance, passthrough, None,
        (nodes, case, (), (), quads),
        transient={'dir': temp_dir, 'members': member_paths,
                   'num_steps': context['num_steps'],
                   'node_count': len(nodes),
                   'edge_count': len(edge_ids), 'layout': result_layout,
                   'time_step': context['time_step']})


def solve(path, *, result_layout='native'):
    """Solve a premeshed THMZ in memory (steady, transient, hygrothermal).

    Args:
        path: Path to a THMZ with SI mesh coordinates. ``CalculationMode``
            selects the steady or transient path; ``SimulateMoisture``
            selects the coupled hygrothermal transient solve. Nothing is
             written; use ``run_thmz`` for the verified atomic file workflow.
        result_layout: 'native' keeps the owned result layout (not a solver
            choice); 'therm' explicitly selects THERM-format transient tables.
            Neither layout certifies physical equivalence to THERM.

    Returns:
        A SolvedResult whose ``members`` mapping is the complete output
        archive; field values are available without serialization.

    Raises:
        ContractError: Invalid or unsupported model, material, mesh or
            boundary; carries a ``THMZ-Exxxx`` code.
        SolveError: The kernel failed or returned incomplete results.
        OSError: The input cannot be read.
    """
    if result_layout not in ('native', 'therm'):
        raise _contract('THMZ-E2005', 'result_layout={!r}: expected native or '
                        'therm'.format(result_layout))
    members, roots, input_digest = _read_archive(Path(path).resolve())
    return _solve_members(members, roots, input_digest, result_layout)


def _verify_result(archive, nodes, case, expected_tags):
    """Read back a written result archive and check structural integrity."""
    if archive.testzip() is not None:
        raise SolveError('Result THMZ failed CRC verification')
    u_factor_data = archive.read(
        'SteadyStateResults.xml').decode('utf-8')
    u_factor_xml = ET.fromstring(u_factor_data)
    xml_cases = u_factor_xml.findall('Case')
    if len(xml_cases) != 1:
        raise SolveError(
            'Result THMZ has incomplete U-factor results')
    if xml_cases[0].findtext('ModelType') != 'U-factor':
        raise SolveError(
            'Result THMZ has incomplete U-factor results')
    xml_records = xml_cases[0].findall('U-factors')
    xml_tags = [record.findtext('Tag') for record in xml_records]
    if (len(xml_tags) != len(expected_tags) or
            set(xml_tags) != expected_tags):
        raise SolveError(
            'Result THMZ has incomplete U-factor results')
    supported_projections = (
        'Total Length', 'Projected X', 'Projected Y',
        'Projected in glass plane', 'Custom Rotation')
    for record in xml_records:
        try:
            delta_t = _finite(float(record.findtext('DeltaT')),
                              'U-factor DeltaT')
            _finite(float(record.findtext('HeatFlux')),
                    'U-factor HeatFlux')
        except (TypeError, ValueError):
            raise SolveError(
                'Result THMZ has incomplete U-factor results')
        projection_types = set()
        for projection in record.findall('Projection'):
            projection_type = projection.findtext('Length-type')
            if (projection_type not in supported_projections or
                    projection_type in projection_types):
                raise SolveError(
                    'Result THMZ has incomplete U-factor results')
            projection_types.add(projection_type)
            try:
                length = _finite(float(projection.findtext('Length')),
                                 'U-factor length')
            except (TypeError, ValueError):
                raise SolveError(
                    'Result THMZ has incomplete U-factor results')
            if length < 0:
                raise SolveError(
                    'Result THMZ has incomplete U-factor results')
            u_factor = projection.findtext('U-factor')
            if u_factor is None:
                if delta_t != 0 and length > 0:
                    raise SolveError(
                        'Result THMZ has incomplete U-factor results')
            else:
                try:
                    _finite(float(u_factor), 'U-factor')
                except (TypeError, ValueError):
                    raise SolveError(
                        'Result THMZ has incomplete U-factor results')
        if 'Total Length' not in projection_types:
            raise SolveError(
                'Result THMZ has incomplete U-factor results')
    steady = fem.steady_state_results.from_string(
        u_factor_data)
    if steady is None or len(steady.cases) != 1:
        raise SolveError(
            'Result THMZ has incomplete U-factor results')
    actual_tags = [record.tag for record in
                   steady.cases[0].steady_state_u_factors]
    if (len(actual_tags) != len(expected_tags) or
            set(actual_tags) != expected_tags):
        raise SolveError(
            'Result THMZ has incomplete U-factor results')
    parsed = fem.steady_state_mesh_results.from_string(
        archive.read('SteadyStateMeshResults.xml').decode('utf-8'))
    if parsed is None or len(parsed.cases) != 1:
        raise SolveError('Result THMZ could not be read back')
    if len(parsed.cases[0].nodes) != len(nodes):
        raise SolveError('Result THMZ is missing node results')
    for expected, actual in zip(case.nodes, parsed.cases[0].nodes):
        if expected.index != actual.index:
            raise SolveError('Result THMZ node labels changed')
        for value in (actual.temperature, actual.x_flux, actual.y_flux):
            _finite(value, 'Serialized result')


def _verify_transient_result(archive, transient):
    """Read back transient result members without loading full series."""
    import csv
    import io
    from itertools import islice
    from . import transient_results as series_io

    if transient.get('layout') == 'therm':
        return _verify_therm_transient_result(archive, transient)
    if archive.testzip() is not None:
        raise SolveError('Result THMZ failed CRC verification')
    try:
        member = series_io.TRANSIENT_RESULT_MEMBERS['geometry']
        content = archive.read(member)
        geometry = series_io.read_geometry_xml(content, member=member)
    except ContractError as error:
        raise SolveError('Result THMZ has incomplete transient results: {}'
                         .format(error)) from error
    if len(geometry['nodes']) != transient['node_count']:
        raise SolveError('Result THMZ transient geometry is missing nodes')
    expected_rows = transient['num_steps'] + 1  # step 0 frame plus steps
    node_ids = tuple(node['id'] for node in geometry['nodes'])
    edge_ids = tuple(range(1, transient['edge_count'] + 1))
    entity_ids = {
        'temperatures': node_ids,
        'humidities': node_ids,
        'heat_flux': node_ids,
        'heat_flux_edges': edge_ids,
        'water_content': node_ids,
        'water_flux': node_ids,
        'water_flux_edges': edge_ids,
        'heat_flux_step_exchange': edge_ids,
        'water_flux_step_exchange': edge_ids,
    }
    member_names = dict(series_io.TRANSIENT_RESULT_MEMBERS,
                        **series_io.TRANSIENT_STEP_EXCHANGE_MEMBERS)
    for key, expected_entities in entity_ids.items():
        member = member_names[key]
        try:
            stream = archive.open(member)
        except KeyError:
            raise SolveError('Result THMZ is missing {}'.format(member))
        rows = 0
        previous = -math.inf
        try:
            with io.TextIOWrapper(stream, encoding='utf-8-sig', newline='') as text:
                reader = csv.reader(text)
                header = next(reader, [])
                buffer = io.StringIO()
                csv.writer(buffer).writerow(header)
                parsed = series_io.read_transient_series(buffer.getvalue())
                if (parsed['labels'][0] != 'Time (s)' or
                        parsed['entities'] != expected_entities):
                    raise _contract('THMZ-E2000',
                                    'result header does not match its entities')
                # Reuse the owned result reader in fixed-size windows. Its
                # convenience API buffers values, so never give it the full
                # member: retained state is bounded by 64 mesh-sized rows.
                while batch := list(islice(reader, 64)):
                    buffer = io.StringIO()
                    csv.writer(buffer).writerows([header] + batch)
                    parsed = series_io.read_transient_series(buffer.getvalue())
                    times = parsed['times']
                    if times:
                        if times[0] < previous:
                            raise _contract('THMZ-E2000',
                                            'result times are decreasing')
                        previous = times[-1]
                    rows += len(times)
        except (ContractError, UnicodeDecodeError, csv.Error) as error:
            detail = (error if isinstance(error, ContractError) else
                      _contract('THMZ-E2000', str(error)))
            raise SolveError('Result THMZ {} is invalid: {}'.format(
                member, detail)) from error
        if rows != expected_rows:
            raise SolveError(
                'Result THMZ {} has {} data rows, expected {}'.format(
                    member, rows, expected_rows))


def _verify_therm_transient_result(archive, transient):
    """Verify all seven tables in lockstep with a one-row memory window."""
    import csv
    from contextlib import ExitStack
    import io
    from . import transient_results as series_io

    if archive.testzip() is not None:
        raise SolveError('Result THMZ failed CRC verification')
    members = series_io.THERM_TRANSIENT_RESULT_MEMBERS
    try:
        # Windows ZipInfo.filename normalizes separators when reading. Its
        # orig_filename retains the actual central-directory member spelling.
        infos = {info.orig_filename: info for info in archive.infolist()}
        for member in members.values():
            count = sum(info.orig_filename == member
                        for info in archive.infolist())
            if count != 1:
                raise SolveError('{}: expected one result member, received {!r}'
                                 .format(member, count))
        content = archive.read(infos[members['geometry']])
        geometry = series_io.read_geometry_xml(
            content, member=members['geometry'])
        node_ids = tuple(range(1, transient['node_count'] + 1))
        labels = [str(value) for value in node_ids]
        actual_ids = tuple(node['id'] for node in geometry['nodes'])
        if sorted(actual_ids) != list(node_ids):
            raise SolveError('THERM Geometry node IDs: received {!r}, expected '
                             '{!r}'.format(actual_ids, node_ids))
        with ExitStack() as stack:
            readers = {}
            headers = {}
            for key, member in members.items():
                if key == 'geometry':
                    continue
                text = stack.enter_context(io.TextIOWrapper(
                    archive.open(infos[member]), encoding='utf-8-sig', newline=''))
                reader = csv.reader(text, strict=True)
                readers[key] = reader
                header = next(reader, None)
                if key.endswith('_edges'):
                    expected = ['Total time', 'Timestep time', '']
                    units = next(reader, None)
                    if units != ['sec', 'sec', '']:
                        raise SolveError('{} units: received {!r}, expected '
                                         'sec,sec,'.format(member, units))
                elif key in ('heat_flux', 'water_flux'):
                    expected = [str(value) + suffix for value in node_ids
                                for suffix in ('-x', '-y')]
                else:
                    expected = ['timestep #', 'error tolerance'] + labels
                if header != expected:
                    raise SolveError('{} header: received {!r}, expected {!r}'
                                     .format(member, header, expected))
                headers[key] = header
            previous = 0.0
            for step in range(1, transient['num_steps'] + 1):
                edge_times, scalar_errors = {}, {}
                for key, reader in readers.items():
                    member = members[key]
                    row = next(reader, None)
                    width = (3 if key.endswith('_edges') else
                             2 * len(node_ids) if key in ('heat_flux', 'water_flux')
                             else len(node_ids) + 2)
                    if row is None or len(row) != width:
                        raise SolveError('{} step {} row: received {!r}, '
                                         'expected {} columns'.format(
                                             member, step, row, width))
                    if key.endswith('_edges'):
                        if row[2] != '':
                            raise SolveError('{} step {} empty column: received '
                                             '{!r}'.format(member, step, row[2]))
                        numbers = row[:2]
                    elif key in ('heat_flux', 'water_flux'):
                        numbers = row
                    else:
                        if row[0] != str(step):
                            raise SolveError('{} timestep #: received {!r}, '
                                             'expected {!r}'.format(
                                                 member, row[0], step))
                        numbers = row[1:]
                    values = []
                    offset = (1 if key.endswith('_edges') or
                              key in ('heat_flux', 'water_flux') else 2)
                    csv_row = step + (2 if key.endswith('_edges') else 1)
                    for column, value in enumerate(numbers, offset):
                        field = headers[key][column - 1]
                        try:
                            number = float(value)
                        except ValueError:
                            raise SolveError('{} row {} column {} field {}: '
                                             'received {!r}, expected finite number'
                                             .format(member, csv_row, column,
                                                     field, value))
                        if not math.isfinite(number):
                            raise SolveError('{} row {} column {} field {}: '
                                             'received {!r}, expected finite number'
                                             .format(member, csv_row, column,
                                                     field, value))
                        values.append(number)
                    if key.endswith('_edges'):
                        time, duration = values
                        expected_time = float(format(
                            step * transient['time_step'], '.6f'))
                        if (time != expected_time or time <= previous or
                                duration <= 0 or not math.isclose(
                                    time - previous, duration,
                                    rel_tol=1e-9, abs_tol=1e-6) or
                                not math.isclose(
                                    duration, transient['time_step'],
                                    rel_tol=1e-9, abs_tol=1e-6)):
                            raise SolveError('{} step {} time/duration: '
                                             'received {!r}, expected time {!r} '
                                             'and duration {!r}'.format(
                                                 member, step, values,
                                                 expected_time,
                                                 transient['time_step']))
                        edge_times[key] = (time, duration)
                    elif key not in ('heat_flux', 'water_flux'):
                        scalar_errors[key] = values[0]
                if edge_times['heat_flux_edges'] != edge_times['water_flux_edges']:
                    raise SolveError('THERM step {} edge times: received {!r}, '
                                     'expected identical tables'.format(
                                         step, edge_times))
                if scalar_errors['humidities'] != scalar_errors['water_content']:
                    raise SolveError('THERM step {} humidity errors: received '
                                     '{!r}, expected identical humidity error'
                                     .format(step, scalar_errors))
                previous = edge_times['heat_flux_edges'][0]
            for key, reader in readers.items():
                member = members[key]
                if key.endswith('_edges'):
                    total = next(reader, None)
                    if total != ['Total', '', '']:
                        raise SolveError('{} Total row: received {!r}, expected '
                                         'Total,,'.format(member, total))
                trailing = next(reader, None)
                if trailing is not None:
                    raise SolveError('{} trailing row: received {!r}, expected '
                                     'end of table'.format(member, trailing))
    except csv.Error as error:
        raise SolveError('{} row {} CSV syntax: received {!r}'.format(
            member, reader.line_num, str(error))) from error
    except (ContractError, KeyError, UnicodeError) as error:
        raise SolveError('Result THMZ THERM layout is invalid: {}'.format(
            error)) from error


def run_thmz(path, output=None, *, result_layout='native'):
    """Solve a premeshed THMZ with solid or cavity materials.

    ``CalculationMode`` dispatches: ``Steady-State`` produces the U-factor
    result members, ``Transient`` produces the ``transient results/`` member
    set streamed one timestep at a time; ``SimulateMoisture`` additionally
    couples the moisture domain (hygrothermal-transient).

    Args:
        path: Path to a THMZ with SI mesh coordinates.
        output: Optional result path; defaults to ``<stem>_solved.thmz``.
             May equal the input path for atomic replacement. Default: None.
        result_layout: 'native' keeps the owned transient layout; 'therm'
            explicitly selects THERM-format transient tables, never steady
            output. This selects a format, not a different native solver.

    Returns:
        Absolute result path as a string. Temperatures are degrees Celsius and
        nodal heat fluxes are W/m2, in the original mesh node order. Tagged
        boundary heat is outward-positive W/m depth, U-factors are W/(m2.K),
        and reference lengths are mm. Zero temperature difference yields no U.
        Added heat flux or differing radiant/air temperatures give an apparent
        heat ratio, not a standard U-factor rating.

    Raises:
        ContractError: Invalid or unsupported model, material, mesh or
            boundary; a ``ValueError`` carrying a ``THMZ-Exxxx`` code.
        SolveError: The kernel failed or the result archive is incomplete;
            a ``RuntimeError``.
        OSError: The input cannot be read or output cannot be published.
    """
    source = Path(path).resolve()
    target = (Path(output).resolve() if output is not None else
              source.with_name(source.stem + '_solved.thmz'))
    if source.suffix.lower() != '.thmz' or target.suffix.lower() != '.thmz':
        raise _contract('THMZ-E1001', 'Input and output paths must end in .thmz')
    result = solve(source, result_layout=result_layout)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
                dir=target.parent, prefix='.' + target.stem + '-',
                suffix='.thmz', delete=False) as stream:
            temporary = Path(stream.name)
            with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as archive:
                for name, source_member in result.member_sources():
                    if isinstance(source_member, Path):
                        if result_layout == 'therm' and '\\' in name:
                            info = zipfile.ZipInfo(name)
                            info.filename = info.orig_filename = name
                            info.compress_type = archive.compression
                            with source_member.open('rb') as incoming:
                                with archive.open(
                                        info, 'w', force_zip64=True) as outgoing:
                                    shutil.copyfileobj(incoming, outgoing,
                                                       length=64 * 1024)
                        else:
                            archive.write(source_member, arcname=name)
                    else:
                        archive.writestr(name, source_member)
            stream.flush()
            os.fsync(stream.fileno())
        with zipfile.ZipFile(temporary) as archive:
            if result._transient is not None:
                _verify_transient_result(archive, result._transient)
            else:
                _verify_result(archive, result._nodes, result._case,
                               result._expected_tags)
        os.replace(temporary, target)
    finally:
        try:
            if temporary is not None and temporary.exists():
                temporary.unlink()
        finally:
            if result._transient is not None:
                result._transient['dir'].cleanup()
    return str(target)


def inspect(path):
    """Check a THMZ archive against the contract without solving it.

    Args:
        path: Path to the archive under inspection.

    Returns:
        An InspectionReport with member names, declared mode, any
        contract_version provenance and validation issues.

    Raises:
        OSError: The input cannot be read at all.
    """
    source = Path(path).resolve()
    members, roots, digest = [], {}, None
    errors, warnings = [], []
    contract_version, solver_version, mode = None, None, None
    try:
        with zipfile.ZipFile(BytesIO(source.read_bytes())) as archive:
            members = archive.namelist()
    except (OSError, zipfile.BadZipFile):
        members = []
    try:
        members_map, roots, digest = _read_archive(source)
        members = list(members_map)
        provenance = members_map.get('pyHygroTherm.json')
        if provenance is not None:
            provenance = json.loads(provenance)
            contract_version = provenance.get('contract_version')
            solver_version = provenance.get('solver_version')
        mode = roots['Model.xml'].findtext(
            'Properties/CalculationOptions/CalculationMode')
        try:
            _inputs(members_map, roots)
        except ContractError as error:
            errors.append(InspectionIssue(error.code, error.args[0]))
        except ValueError as error:
            errors.append(InspectionIssue('THMZ-E2000', str(error)))
    except ContractError as error:
        errors.append(InspectionIssue(error.code, error.args[0]))
    return InspectionReport(
        tuple(members), contract_version=contract_version,
        solver_version=solver_version, mode=mode, errors=tuple(errors),
        warnings=tuple(warnings), input_sha256=digest)
