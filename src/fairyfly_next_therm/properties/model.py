# coding=utf-8
"""Model Therm Properties."""
import math
try:
    from itertools import izip as zip  # python 2
except ImportError:
    pass   # python 3

from ladybug_geometry.geometry2d import Point2D
from ladybug_geometry.geometry3d import Vector3D, Plane, Face3D, \
    Polyline3D, Polyface3D

from fairyfly.extensionutil import model_extension_dicts
from fairyfly.typing import invalid_dict_error
from fairyfly.checkdup import check_duplicate_identifiers
from fairyfly.units import conversion_factor_to_meters
from fairyfly.shape import Shape

from ..material.dictutil import dict_to_material, dict_abridged_to_material, \
    MATERIAL_TYPES
from ..material.gas import PureGas, Gas
from ..material.cavity import CavityMaterial
from ..condition.dictutil import dict_to_condition


class ModelThermProperties(object):
    """Therm Properties for Fairyfly-Next Model.

    Args:
        host: A fairyfly Model object that hosts these properties.

    Properties:
        * host
        * materials
        * conditions
        * gases
        * therm_plane
    """
    # dictionary mapping validation error codes to a corresponding check function
    ERROR_MAP = {
        '210001': 'check_duplicate_material_identifiers',
        '210002': 'check_duplicate_condition_identifiers',
        '210003': 'check_duplicate_gas_identifiers'
    }

    def __init__(self, host):
        """Initialize Model therm properties."""
        self._host = host

    @property
    def host(self):
        """Get the Model object hosting these properties."""
        return self._host

    @property
    def materials(self):
        """Get a list of all unique materials assigned to Shapes.

        The list preserves first-encounter order across the Shapes so that
        serialized output (and any per-name processing built on it) is stable.
        """
        materials = []
        for shape in self.host.shapes:
            mat = shape.properties.therm.material
            if mat not in materials:
                materials.append(mat)
        return materials

    @property
    def conditions(self):
        """Get a list of all unique conditions contained within the model.

        The list preserves first-encounter order across the Boundaries.
        """
        conditions = []
        for bnd in self.host.boundaries:
            con = bnd.properties.therm.condition
            if con not in conditions:
                conditions.append(con)
        return conditions

    @property
    def gases(self):
        """Get a list of all unique gases contained within the model.

        The list preserves first-encounter order across the materials.
        """
        gases = []
        for mat in self.materials:
            if isinstance(mat, CavityMaterial):
                gas = mat.gas
                if gas not in gases:
                    gases.append(gas)
        return gases

    @property
    def therm_plane(self):
        """Get a ladybug-geometry Plane that represents the 2D THERM canvas."""
        ang_tol = self.host.angle_tolerance
        origin = self.host.shapes[0].vertices[0]
        normal = self.host.shapes[0].geometry.normal
        up_vec = math.degrees(Vector3D(0, 0, 1).angle(normal))
        if up_vec < ang_tol or up_vec > 180 - ang_tol:
            bp = Plane(o=origin)
        else:
            if normal.z < 0:
                normal = normal.reverse()
            bp = Plane(n=normal, o=origin)
        # Bound in the section plane; a 3D bounding-box corner can be off-plane.
        vertices = [bp.xyz_to_xy(v) for s in self.host.shapes for v in s.vertices]
        origin = bp.xy_to_xyz(Point2D(
            min(v.x for v in vertices), max(v.y for v in vertices)))
        conversion = 0.001 / conversion_factor_to_meters(self.host.units)
        t_vec = (bp.x * -100 * conversion) + (bp.y * 100 * conversion)
        offset_origin = origin.move(t_vec)
        return Plane(n=bp.n, o=offset_origin)

    @property
    def problem_areas(self):
        """Get disconnected regions and holes without changing the Shapes.

        Inspection uses the host model's tolerance, expressed in its units.

        Returns:
            A tuple of two lists of Polyline3D objects in model units:
            disconnected outer regions and internal holes, respectively.
        """
        plane = self.therm_plane
        tolerance = self.host.tolerance
        shapes = [shape.duplicate() for shape in self.host.shapes]
        Shape.intersect_adjacency(shapes, tolerance, plane)
        # ensure that there is only one contiguous shape without holes
        shape_geos = [shape.geometry for shape in shapes]
        polyface = Polyface3D.from_faces(shape_geos, tolerance=tolerance)
        outer_edges = polyface.naked_edges
        joined_boundary = Polyline3D.join_segments(outer_edges, tolerance=tolerance)
        problem_regions, problem_holes = [], []
        if len(joined_boundary) > 1:
            join_faces = [Face3D(poly.vertices) for poly in joined_boundary]
            merged_faces = Face3D.merge_faces_to_holes(join_faces, tolerance)
            if len(merged_faces) > 1:
                for region in merged_faces:
                    problem_regions.append(Polyline3D(region.boundary))
            for mf in merged_faces:
                if mf.has_holes:
                    for hole in mf.holes:
                        problem_holes.append(Polyline3D(hole))
        return problem_regions, problem_holes

    def check_for_extension(self, raise_exception=True, detailed=False):
        """Check that the Model is valid for Therm simulation.

        This process includes all relevant fairyfly-core checks as well as checks
        that apply only for Therm.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if any errors are found. If False, this method will simply
                return a text string with all errors that were found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A text string with all errors that were found or a list if detailed is True.
            This string (or list) will be empty if no errors were found.
        """
        # set up defaults to ensure the method runs correctly
        detailed = False if raise_exception else detailed
        msgs = []
        tol = self.host.tolerance

        # perform checks for duplicate identifiers, which might mess with other checks
        msgs.append(self.host.check_all_duplicate_identifiers(False, detailed))

        # perform several checks for the Fairyfly schema geometry rules
        msgs.append(self.host.check_planar(tol, False, detailed))
        msgs.append(self.host.check_self_intersecting(tol, False, detailed))

        # output a final report of errors or raise an exception
        full_msgs = [msg for msg in msgs if msg]
        if detailed:
            return [m for msg in full_msgs for m in msg]
        full_msg = '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_all(self, raise_exception=True, detailed=False):
        """Check all of the aspects of the Model therm properties.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if any errors are found. If False, this method will simply
                return a text string with all errors that were found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A text string with all errors that were found or a list if detailed is True.
            This string (or list) will be empty if no errors were found.
        """
        # set up defaults to ensure the method runs correctly
        detailed = False if raise_exception else detailed
        msgs = []
        # perform checks for duplicate identifiers
        msgs.append(self.check_all_duplicate_identifiers(False, detailed))
        # output a final report of errors or raise an exception
        full_msgs = [msg for msg in msgs if msg]
        if detailed:
            return [m for msg in full_msgs for m in msg]
        full_msg = '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_all_duplicate_identifiers(self, raise_exception=True, detailed=False):
        """Check that there are no duplicate identifiers for any therm objects.

        This includes Materials, Gases, and Conditions.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if any duplicate identifiers are found. If False, this method will simply
                return a text string with all errors that were found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A text string with all errors that were found or a list if detailed is True.
            This string (or list) will be empty if no errors were found.
        """
        # set up defaults to ensure the method runs correctly
        detailed = False if raise_exception else detailed
        msgs = []
        # perform checks for duplicate identifiers
        msgs.append(self.check_duplicate_material_identifiers(False, detailed))
        msgs.append(self.check_duplicate_condition_identifiers(False, detailed))
        msgs.append(self.check_duplicate_gas_identifiers(False, detailed))
        # output a final report of errors or raise an exception
        full_msgs = [msg for msg in msgs if msg]
        if detailed:
            return [m for msg in full_msgs for m in msg]
        full_msg = '\n'.join(full_msgs)
        if raise_exception and len(full_msgs) != 0:
            raise ValueError(full_msg)
        return full_msg

    def check_duplicate_material_identifiers(self, raise_exception=True, detailed=False):
        """Check that there are no duplicate Material identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers(
            self.materials, raise_exception, 'Material',
            detailed, '210001', 'Therm', error_type='Duplicate Material Identifier')

    def check_duplicate_condition_identifiers(
            self, raise_exception=True, detailed=False):
        """Check that there are no duplicate Condition identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers(
            self.conditions, raise_exception, 'Condition',
            detailed, '210002', 'Therm', error_type='Duplicate Condition Identifier')

    def check_duplicate_gas_identifiers(
            self, raise_exception=True, detailed=False):
        """Check that there are no duplicate Gas identifiers in the model.

        Args:
            raise_exception: Boolean to note whether a ValueError should be raised
                if duplicate identifiers are found. (Default: True).
            detailed: Boolean for whether the returned object is a detailed list of
                dicts with error info or a string with a message. (Default: False).

        Returns:
            A string with the message or a list with a dictionary if detailed is True.
        """
        return check_duplicate_identifiers(
            self.gases, raise_exception, 'Gas',
            detailed, '020003', 'Therm', error_type='Duplicate Gas Identifier')

    def apply_properties_from_dict(self, data):
        """Apply the therm properties of a dictionary to the host Model of this object.

        Args:
            data: A dictionary representation of an entire fairyfly-core Model.
                Note that this dictionary must have ModelThermProperties in order
                for this method to successfully apply the therm properties.
        """
        assert 'therm' in data['properties'], \
            'Dictionary possesses no ModelThermProperties.'
        materials, conditions, _, _ = self.load_properties_from_dict(data)

        # collect lists of therm property dictionaries
        shape_t_dicts, boundary_t_dicts = model_extension_dicts(data, 'therm', [], [])

        # apply therm properties to objects using the therm property dictionaries
        for shape, s_dict in zip(self.host.shapes, shape_t_dicts):
            if s_dict is not None:
                shape.properties.therm.apply_properties_from_dict(
                    s_dict, materials)
        for bound, b_dict in zip(self.host.boundaries, boundary_t_dicts):
            if b_dict is not None:
                bound.properties.therm.apply_properties_from_dict(b_dict, conditions)

    def to_dict(self):
        """Return Model therm properties as a dictionary."""
        base = {'therm': {'type': 'ModelThermProperties'}}
        # add the materials to the dictionary
        all_mats = self.materials
        gases, pure_gases = [], []
        if len(all_mats) != 0:
            base['therm']['materials'] = []
            for mat in all_mats:
                if isinstance(mat, CavityMaterial):
                    base['therm']['materials'].append(mat.to_dict(abridged=True))
                    gases.append(mat.gas)
                    for pg in mat.gas.pure_gases:
                        pure_gases.append(pg)
                else:  # SolidMaterial
                    base['therm']['materials'].append(mat.to_dict())
            if len(gases) != 0:
                base['therm']['gases'] = [g.to_dict(abridged=True) for g in set(gases)]
                base['therm']['pure_gases'] = [pg.to_dict() for pg in set(pure_gases)]
        # add the conditions to the dictionary
        all_conds = self.conditions
        if len(all_conds) != 0:
            base['therm']['conditions'] = []
            for con in all_conds:
                base['therm']['conditions'].append(con.to_dict())
        return base

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        Args:
            new_host: A new Model object that hosts these properties.
                If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        return ModelThermProperties(_host)

    @staticmethod
    def load_properties_from_dict(data, skip_invalid=False):
        """Load model therm properties of a dictionary to Python objects.

        Loaded objects include Materials, Boundaries, Gases, and PureGases.

        The function is called when re-serializing a Model object from a dictionary
        to load fairyfly_next_therm objects into their Python object form before
        applying them to the Model geometry.

        Args:
            data: A dictionary representation of an entire fairyfly-core Model.
                Note that this dictionary must have ModelThermProperties in order
                for this method to successfully load the therm properties.
            skip_invalid: A boolean to note whether objects that cannot be loaded
                should be ignored (True) or whether an exception should be raised
                about the invalid object (False). (Default: False).

        Returns:
            A tuple with eight elements

            -   materials -- A dictionary with identifiers of materials as keys
                and Python material objects as values.

            -   conditions -- A dictionary with identifiers of conditions
                as keys and Python boundary objects as values.

            -   gases -- A dictionary with identifiers of gases as keys and
                Python gas objects as values.

            -   pure_gases -- A dictionary with identifiers of pure gases
                and Python PureGas objects as values.
        """
        assert 'therm' in data['properties'], \
            'Dictionary possesses no ModelThermProperties.'

        # process all pure gases in the ModelThermProperties dictionary
        pure_gases = {}
        if 'pure_gases' in data['properties']['therm'] and \
                data['properties']['therm']['pure_gases'] is not None:
            for pg in data['properties']['therm']['pure_gases']:
                try:
                    pure_gases[pg['identifier']] = PureGas.from_dict(pg)
                except Exception as e:
                    if not skip_invalid:
                        invalid_dict_error(pg, e)

        # process all gases in the ModelThermProperties dictionary
        gases = {}
        if 'gases' in data['properties']['therm'] and \
                data['properties']['therm']['gases'] is not None:
            for g in data['properties']['therm']['gases']:
                try:
                    if g['type'] == 'Gas':
                        gases[g['identifier']] = Gas.from_dict(g)
                    else:
                        gases[g['identifier']] = Gas.from_dict_abridged(g, pure_gases)
                except Exception as e:
                    if not skip_invalid:
                        invalid_dict_error(g, e)

        # process all materials in the ModelThermProperties dictionary
        materials = {}
        if 'materials' in data['properties']['therm'] and \
                data['properties']['therm']['materials'] is not None:
            for mat in data['properties']['therm']['materials']:
                try:
                    if mat['type'] in MATERIAL_TYPES:
                        materials[mat['identifier']] = dict_to_material(mat)
                    else:
                        materials[mat['identifier']] = \
                            dict_abridged_to_material(mat, gases)
                except Exception as e:
                    if not skip_invalid:
                        invalid_dict_error(mat, e)

        # process all conditions in the ModelThermProperties dictionary
        conditions = {}
        if 'conditions' in data['properties']['therm'] and \
                data['properties']['therm']['conditions'] is not None:
            for con in data['properties']['therm']['conditions']:
                try:
                    conditions[con['identifier']] = dict_to_condition(con)
                except Exception as e:
                    if not skip_invalid:
                        invalid_dict_error(con, e)

        return materials, conditions, gases, pure_gases

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Model Therm Properties: [host: {}]'.format(self.host.display_name)
