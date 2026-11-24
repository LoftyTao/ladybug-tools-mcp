# coding=utf-8
"""Create the baseline THMZ mesh with Rhino's native quad remesher."""
import math
import xml.etree.ElementTree as ET

from ladybug_geometry.geometry2d import Point2D, Polygon2D


def _finite(text, field):
    try:
        value = float(text)
    except (TypeError, ValueError):
        raise ValueError('{} must be a finite number'.format(field))
    if math.isnan(value) or math.isinf(value):
        raise ValueError('{} must be a finite number'.format(field))
    return value


def _quad_remesh(model_xml, target_quad_count):
    """Remesh joined material faces while retaining their shared boundaries."""
    try:
        import Rhino
    except ImportError:
        raise RuntimeError('rhino_mesh=True requires RhinoCommon.')

    polygons = model_xml.findall('Polygons/Polygon')
    if not polygons or any(p.findtext('Type') != 'Material' for p in polygons):
        raise ValueError('Rhino meshing requires material polygons.')
    tolerance = _finite(
        model_xml.findtext('Properties/Miscellaneous/CheckingTolerance') or '0.1',
        'CheckingTolerance')
    breps = []
    outlines = []
    for polygon in polygons:
        points = [Rhino.Geometry.Point3d(
            _finite(point.findtext('x'), 'Polygon x'),
            _finite(point.findtext('y'), 'Polygon y'), 0)
            for point in polygon.findall('Points/Point')]
        if len(points) < 3:
            raise ValueError('The exported polygon requires at least three points.')
        points.append(points[0])
        planar = Rhino.Geometry.Brep.CreatePlanarBreps(
            Rhino.Geometry.PolylineCurve(points), tolerance)
        if planar is None or len(planar) != 1:
            raise ValueError('Rhino could not make a planar material face.')
        breps.append(planar[0])
        outlines.append([(point.X, point.Y) for point in points[:-1]])
    joined = Rhino.Geometry.Brep.JoinBreps(breps, tolerance)
    if joined is None or len(joined) != 1:
        raise ValueError('Material faces must join into one contiguous Brep.')

    parameters = Rhino.Geometry.QuadRemeshParameters()
    parameters.TargetQuadCount = int(target_quad_count)
    parameters.PreserveMeshArrayEdgesMode = 2  # Strict Brep face boundaries.
    # A straight Brep edge can be remeshed across a boundary-condition endpoint.
    # Rhino's edge-loop guides retain these endpoints as actual mesh nodes.
    xs = [point[0] for outline in outlines for point in outline]
    ys = [point[1] for outline in outlines for point in outline]
    extent = 2 * max(max(xs) - min(xs), max(ys) - min(ys))
    guides, guided_points = [], set()
    for boundary in model_xml.findall('Boundaries/Boundary'):
        if boundary.findtext('Type') != 'Boundary Condition':
            continue
        for tag in ('StartPoint', 'EndPoint'):
            point = boundary.find(tag)
            xy = (_finite(point.findtext('x'), 'Boundary x'),
                  _finite(point.findtext('y'), 'Boundary y'))
            if xy in guided_points:
                continue
            for outline in outlines:
                for index, vertex in enumerate(outline):
                    if vertex != xy:
                        continue
                    before = outline[index - 1]
                    after = outline[(index + 1) % len(outline)]
                    if not _point_on_segment(xy, before, after):
                        continue
                    dx, dy = after[0] - before[0], after[1] - before[1]
                    length = math.hypot(dx, dy)
                    nx, ny = -dy / length, dx / length
                    start = Rhino.Geometry.Point3d(
                        xy[0] - nx * extent, xy[1] - ny * extent, 0)
                    end = Rhino.Geometry.Point3d(
                        xy[0] + nx * extent, xy[1] + ny * extent, 0)
                    guides.append(Rhino.Geometry.LineCurve(start, end))
                    guided_points.add(xy)
                    break
                if xy in guided_points:
                    break
    if guides:
        parameters.GuideCurveInfluence = 2  # Interpolate an edge loop.
        mesh = Rhino.Geometry.Mesh.QuadRemeshBrep(joined[0], parameters, guides)
    else:
        mesh = Rhino.Geometry.Mesh.QuadRemeshBrep(joined[0], parameters)
    if mesh is None or mesh.Faces.Count == 0:
        raise ValueError('Rhino QuadRemeshBrep did not produce a mesh.')
    return mesh


def _condition_values(boundary_conditions, name):
    matches = [item for item in boundary_conditions.findall('BoundaryCondition')
               if item.findtext('Name') == name]
    if len(matches) != 1:
        raise ValueError('Boundary {} must map to one steady condition.'.format(name))
    condition = matches[0]
    simple = condition.find('Simplified')
    if simple is not None:
        return (_finite(simple.findtext('FilmCoefficient'), 'FilmCoefficient'),
                _finite(simple.findtext('Temperature'), 'Temperature'))
    convection = condition.find('Comprehensive/Convection')
    if convection is None:
        raise ValueError('Boundary {} has no convection condition.'.format(name))
    return (_finite(convection.findtext('FilmCoefficient'), 'FilmCoefficient'),
            _finite(convection.findtext('Temperature'), 'Temperature'))


def _point_on_segment(point, start, end, tolerance=1e-3):
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= tolerance:
        return False
    px, py = point[0] - start[0], point[1] - start[1]
    projection = (px * dx + py * dy) / length
    distance = abs(px * dy - py * dx) / length
    return distance <= tolerance and -tolerance <= projection <= length + tolerance


def _covered(boundary, segments, tolerance=1e-3):
    start, end = boundary
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = math.hypot(dx, dy)
    if length <= tolerance:
        return False
    intervals = []
    for first, second in segments:
        values = [((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length
                  for point in (first, second)]
        intervals.append((min(values), max(values)))
    cursor = 0
    for low, high in sorted(intervals):
        if abs(low - cursor) > tolerance:
            return False
        cursor = max(cursor, high)
    return cursor >= length - tolerance


def _transient_step_value(condition, key):
    """The first-timestep value of a Transient condition field or None."""
    if condition.timesteps:
        return condition.timesteps[min(condition.timesteps)].get(key)
    return None


def _transient_boundary_value(condition, name):
    """Resolve a Transient condition into a mesh segment record.

    Returns a (kind, value_a, value_b) tuple where kind is 'temperature',
    'flux', or 'convection' and the values are the two segment quantities
    in the order written to Mesh.xml (temperature for Temperatures,
    flux1/flux2 for Fluxes, film/temperature for Convections).

    A humidity-only Dirichlet pin (use_humidity without use_temperature)
    is emitted as a Temperatures segment with a 0 temperature: Mesh.xml
    has no humidity segment type and the solver reads only the
    HumidityTimestep series for such pins, so the Temperatures field is
    inert per the ticket-09 kernel convention.
    """
    if condition.use_humidity and condition.bc_model == 'Dirichlet' \
            and not condition.use_temperature:
        humidity = _transient_step_value(condition, 'humidity')
        if humidity is None:
            humidity = condition.imposed_humidity
        if humidity is None:
            raise ValueError(
                'Transient boundary {} needs a humidity value.'.format(name))
        return ('temperature', 0.0, None)
    if condition.bc_model == 'Dirichlet' or condition.use_temperature:
        value = _transient_step_value(condition, 'surface_temperature')
        if value is None:
            value = condition.imposed_temperature
        if value is None:
            raise ValueError(
                'Transient boundary {} needs an imposed temperature.'.format(
                    name))
        return ('temperature', float(value), None)
    if condition.use_heat_flux:
        value = _transient_step_value(condition, 'heat_flux')
        if value is None:
            value = condition.heat_flux
        if value is None:
            raise ValueError(
                'Transient boundary {} needs a heat flux.'.format(name))
        return ('flux', float(value), float(value))
    # Neumann convection; dynamic film models carry a 0 placeholder because
    # Mesh.xml has no per-step storage and the kernel recomputes the film.
    film = condition.film_coefficient
    if film is None:
        film = _transient_step_value(condition, 'film_coefficient')
    if film is None:
        film = 0
    temperature = condition.temperature
    if temperature is None:
        temperature = _transient_step_value(condition, 'temperature')
    if temperature is None:
        raise ValueError(
            'Transient boundary {} needs a temperature.'.format(name))
    return ('convection', float(film), float(temperature))


def mesh_to_xml(model_xml, boundary_conditions, mesh,
                transient_conditions=None):
    """Serialize a conforming Rhino Q4 mesh into LibraryFEM format.

    Args:
        model_xml: The exported THERM model XML element.
        boundary_conditions: The exported steady boundary conditions element.
        mesh: A Rhino mesh whose vertices are in exported model XY millimeters.
        transient_conditions: An optional dictionary of Transient condition
            objects keyed by their display name. Boundaries whose Name matches
            a key are exported as Temperatures/Fluxes/Convections segments
            driven by the record instead of a SteadyStateBC lookup.
            (Default: None).

    Returns:
        An XML element with zero-based Q4 node references and SI mesh coordinates
        in meters relative to the model's GlazingOrigin.

    Raises:
        ValueError: The mesh, material assignment, or boundary mapping is invalid.

    Mesh material IDs are one-based, in first-occurrence order of distinct
    Model.xml MaterialUUID values. Polygon IDs remain independent labels.
    Transient radiation models are not emitted: the Radiations and
    RadiationEnclosures segment groups carry no label, so they cannot be
    bound to a model boundary.
    """
    transient_conditions = transient_conditions or {}
    polygons = model_xml.findall('Polygons/Polygon')
    if not polygons or any(p.findtext('Type') != 'Material' for p in polygons):
        raise ValueError('Rhino meshing requires material polygons.')
    regions = [Polygon2D(tuple(Point2D(
        _finite(point.findtext('x'), 'Polygon x'),
        _finite(point.findtext('y'), 'Polygon y'))
        for point in polygon.findall('Points/Point'))) for polygon in polygons]
    material_ids = {}
    region_materials = []
    for polygon in polygons:
        material = polygon.findtext('MaterialUUID')
        if not material and len(polygons) > 1:
            raise ValueError('Material polygons must identify their MaterialUUID.')
        material = material.lower() if material else None
        if material not in material_ids:
            material_ids[material] = len(material_ids) + 1
        region_materials.append(material_ids[material])

    origin = model_xml.find('GlazingOrigin')
    if origin is None:
        raise ValueError('Model.xml is missing GlazingOrigin.')
    origin_x = _finite(origin.findtext('x'), 'GlazingOrigin x')
    origin_y = _finite(origin.findtext('y'), 'GlazingOrigin y')
    vertices = [(_finite(v.X, 'Mesh vertex x'), _finite(v.Y, 'Mesh vertex y'),
                 _finite(v.Z, 'Mesh vertex z')) for v in mesh.Vertices]
    faces = []
    for face in mesh.Faces:
        if face.D == face.C:
            raise ValueError('Rhino mesh contains a triangle; Q4 elements are required.')
        quad = (int(face.A), int(face.B), int(face.C), int(face.D))
        if len(set(quad)) != 4 or any(i < 0 or i >= len(vertices) for i in quad):
            raise ValueError('Rhino mesh contains an invalid Q4 face.')
        faces.append(quad)
    if not vertices or not faces:
        raise ValueError('Rhino mesh requires vertices and Q4 faces.')

    # Discard unused native vertices so the serialized mesh has no orphan nodes.
    used = sorted(set(i for face in faces for i in face))
    reindex = dict((old, new) for new, old in enumerate(used))
    points = [vertices[i] for i in used]
    faces = [tuple(reindex[i] for i in face) for face in faces]
    if len(set((round(p[0], 9), round(p[1], 9)) for p in points)) != len(points):
        raise ValueError('Rhino mesh contains coincident vertices.')

    # Rhino may orient the mesh either way; pyHygroTherm requires CCW Q4s.
    oriented = []
    for index, face in enumerate(faces, 1):
        cross_products = []
        for i in range(4):
            a, b, c = (points[face[(i + j) % 4]] for j in range(3))
            cross_products.append((b[0] - a[0]) * (c[1] - b[1]) -
                                  (b[1] - a[1]) * (c[0] - b[0]))
        if all(cross < 0 for cross in cross_products):
            face = (face[0], face[3], face[2], face[1])
            cross_products = [-cross for cross in reversed(cross_products)]
        if not all(cross > 0 for cross in cross_products):
            raise ValueError('Rhino face {} is degenerate or not a convex Q4.'.format(
                index))
        oriented.append(face)
    faces = oriented

    # IDs follow first occurrence of each material UUID, independently of polygon
    # labels. Region perimeter checks reject crossed or unshared interfaces.
    face_regions = []
    region_edges = [dict() for _ in regions]
    for face in faces:
        corners = [Point2D(*points[i][:2]) for i in face]
        center = Point2D(sum(p.x for p in corners) / 4,
                         sum(p.y for p in corners) / 4)
        matches = [i for i, region in enumerate(regions)
                   if region.point_relationship(center, 1e-3) == 1 and
                   all(region.point_relationship(p, 1e-3) >= 0 for p in corners)]
        if len(matches) != 1:
            raise ValueError('Rhino Q4 must belong to exactly one material polygon.')
        region_index = matches[0]
        face_regions.append(region_index)
        counts = region_edges[region_index]
        for i in range(4):
            edge = tuple(sorted((face[i], face[(i + 1) % 4])))
            counts[edge] = counts.get(edge, 0) + 1
    for region, counts in zip(regions, region_edges):
        sides = [(tuple(s.p1), tuple(s.p2)) for s in region.segments]
        covered_sides = [[] for _ in sides]
        for edge, count in counts.items():
            if count != 1:
                continue
            endpoints = [points[i][:2] for i in edge]
            matches = [i for i, side in enumerate(sides)
                       if all(_point_on_segment(p, *side) for p in endpoints)]
            if len(matches) != 1:
                raise ValueError('Rhino mesh does not preserve material interfaces.')
            covered_sides[matches[0]].append(endpoints)
        if any(not _covered(side, spans)
               for side, spans in zip(sides, covered_sides)):
            raise ValueError('Rhino mesh leaves a material interface gap or overlap.')

    boundaries = {}
    for boundary in model_xml.findall('Boundaries/Boundary'):
        if boundary.findtext('Type') == 'Frame Cavity':
            continue  # The cavity model handles its internal heat exchange.
        boundary_id = boundary.findtext('ID')
        name = boundary.findtext('Name')
        if (boundary.findtext('Type') != 'Boundary Condition' or
                not boundary_id or not name):
            raise ValueError('Native mesh export supports boundary conditions only.')
        first, second = boundary.find('StartPoint'), boundary.find('EndPoint')
        segment = ((_finite(first.findtext('x'), 'Boundary start x'),
                    _finite(first.findtext('y'), 'Boundary start y')),
                   (_finite(second.findtext('x'), 'Boundary end x'),
                    _finite(second.findtext('y'), 'Boundary end y')))
        key = int(boundary_id)
        if key in boundaries:
            raise ValueError('Model boundary IDs must be unique.')
        if name in transient_conditions:
            value = _transient_boundary_value(transient_conditions[name], name)
        else:
            value = _condition_values(boundary_conditions, name)
        boundaries[key] = (name, segment, value)

    # Build oriented exterior edges directly from Rhino's quad topology.
    edge_counts = {}
    for face in faces:
        for i in range(4):
            edge = (face[i], face[(i + 1) % 4])
            key = tuple(sorted(edge))
            edge_counts[key] = edge_counts.get(key, 0) + 1
    if any(count > 2 for count in edge_counts.values()):
        raise ValueError('Rhino mesh contains a nonmanifold edge.')

    mesh_xml = ET.Element('Mesh')
    ET.SubElement(mesh_xml, 'Version').text = '1'
    case = ET.SubElement(mesh_xml, 'Case')
    ET.SubElement(case, 'ModelType').text = 'U-factor'
    nodes_xml = ET.SubElement(case, 'Nodes')
    for index, point in enumerate(points, 1):
        if abs(point[2]) > 1e-3:
            raise ValueError('Rhino mesh must lie in the exported model plane.')
        node = ET.SubElement(nodes_xml, 'Node')
        ET.SubElement(node, 'index').text = str(index)
        ET.SubElement(node, 'x').text = str(round((point[0] - origin_x) / 1000, 9))
        ET.SubElement(node, 'y').text = str(round((point[1] - origin_y) / 1000, 9))

    elements_xml = ET.SubElement(case, 'Elements')
    for index, (face, region) in enumerate(zip(faces, face_regions), 1):
        element = ET.SubElement(elements_xml, 'Element')
        ET.SubElement(element, 'index').text = str(index)
        for i, node_index in enumerate(face, 1):
            ET.SubElement(element, 'node{}'.format(i)).text = str(node_index)
        ET.SubElement(element, 'materialID').text = str(region_materials[region])

    bc_segments = ET.SubElement(case, 'BCSegments')
    # groups are written in schema order; Fluxes and Temperatures only appear
    # when a Transient condition drives them
    fluxes = temperatures = None
    if transient_conditions:
        fluxes = ET.Element('Fluxes')
        temperatures = ET.Element('Temperatures')
    convections = ET.SubElement(bc_segments, 'Convections')
    covered = dict((boundary_id, []) for boundary_id in boundaries)
    exterior = [edge for edge, count in edge_counts.items() if count == 1]
    oriented_edges = {(min(face[i], face[(i + 1) % 4]),
                       max(face[i], face[(i + 1) % 4])):
                      (face[i], face[(i + 1) % 4])
                      for face in faces for i in range(4)
                      if edge_counts[(min(face[i], face[(i + 1) % 4]),
                                      max(face[i], face[(i + 1) % 4]))] == 1}
    flux_index = 0
    temperature_nodes = {}
    for index, edge in enumerate(exterior, 1):
        first, second = (points[i][:2] for i in oriented_edges[edge])
        matches = [boundary_id for boundary_id, value in boundaries.items()
                   if _point_on_segment(first, *value[1]) and
                   _point_on_segment(second, *value[1])]
        if len(matches) != 1:
            raise ValueError(
                'Mesh exterior edge does not match exactly one model boundary.')
        boundary_id = matches[0]
        name, segment, value = boundaries[boundary_id]
        covered[boundary_id].append((first, second))
        if isinstance(value, tuple) and len(value) == 3:
            kind, value_a, value_b = value
            if kind == 'temperature':
                for node_index in oriented_edges[edge]:
                    existing = temperature_nodes.get(node_index)
                    if existing is not None:
                        if existing[0] != value_a:
                            raise ValueError(
                                'Imposed temperatures on a shared mesh node '
                                'do not agree.')
                        continue
                    temperature_nodes[node_index] = (value_a, boundary_id)
                    record = ET.SubElement(temperatures, 'Temperature')
                    ET.SubElement(record, 'node').text = str(node_index)
                    ET.SubElement(record, 'temperature').text = str(value_a)
                    ET.SubElement(record, 'label').text = str(boundary_id)
            elif kind == 'flux':
                flux_index += 1
                record = ET.SubElement(fluxes, 'Flux')
                ET.SubElement(record, 'index').text = str(flux_index)
                ET.SubElement(record, 'node1').text = \
                    str(oriented_edges[edge][0])
                ET.SubElement(record, 'node2').text = \
                    str(oriented_edges[edge][1])
                ET.SubElement(record, 'flux1').text = str(value_a)
                ET.SubElement(record, 'flux2').text = str(value_b)
                ET.SubElement(record, 'label').text = str(boundary_id)
            else:  # transient convection
                film, temperature = value_a, value_b
                if film < 0:
                    raise ValueError('Boundary {} has a negative film '
                                     'coefficient.'.format(name))
                convection = ET.SubElement(convections, 'Convection')
                ET.SubElement(convection, 'index').text = str(index)
                ET.SubElement(convection, 'node1').text = \
                    str(oriented_edges[edge][0])
                ET.SubElement(convection, 'node2').text = \
                    str(oriented_edges[edge][1])
                ET.SubElement(convection, 'filmCoefficient').text = str(film)
                ET.SubElement(convection, 'temperature1').text = \
                    str(temperature)
                ET.SubElement(convection, 'temperature2').text = \
                    str(temperature)
                ET.SubElement(convection, 'label').text = str(boundary_id)
            continue
        film, temperature = value
        if film < 0:
            raise ValueError('Boundary {} has a negative film coefficient.'.format(name))
        convection = ET.SubElement(convections, 'Convection')
        ET.SubElement(convection, 'index').text = str(index)
        ET.SubElement(convection, 'node1').text = str(oriented_edges[edge][0])
        ET.SubElement(convection, 'node2').text = str(oriented_edges[edge][1])
        ET.SubElement(convection, 'filmCoefficient').text = str(film)
        ET.SubElement(convection, 'temperature1').text = str(temperature)
        ET.SubElement(convection, 'temperature2').text = str(temperature)
        ET.SubElement(convection, 'label').text = str(boundary_id)
    if transient_conditions:
        if len(fluxes):
            bc_segments.insert(0, fluxes)
        if len(temperatures):
            bc_segments.insert(1 if len(fluxes) else 0, temperatures)
    if any(not _covered(value[1], covered[boundary_id])
           for boundary_id, value in boundaries.items()):
        raise ValueError('Rhino mesh does not cover every exported boundary.')
    return mesh_xml


def create_mesh_xml(model_xml, boundary_conditions, target_quad_count,
                    transient_conditions=None):
    """Generate and serialize Rhino's native quadrilateral mesh.

    Args:
        model_xml: The exported THERM model XML element.
        boundary_conditions: The exported steady boundary conditions element.
        target_quad_count: Rhino TargetQuadCount, not a guaranteed element count.
        transient_conditions: An optional dictionary of Transient condition
            objects keyed by display name for transient boundary segments.
            (Default: None).

    Returns:
        The LibraryFEM Mesh XML element with coordinates in meters.

    Raises:
        RuntimeError: RhinoCommon is unavailable.
        ValueError: The model or Rhino mesh is outside the supported Q4 baseline.

    The existing mesh parameter maps to Rhino TargetQuadCount. The value is a
    target, and does not reproduce upstream Fairyfly's prior energy-error estimator.
    """
    return mesh_to_xml(
        model_xml, boundary_conditions,
        _quad_remesh(model_xml, target_quad_count), transient_conditions)
