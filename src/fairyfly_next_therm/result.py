# coding=utf-8
"""Module for parsing THERM results."""
from __future__ import division

import os
import zipfile
import json
import re
import xml.etree.ElementTree as ET

from ladybug_geometry.geometry2d import Vector2D, Point2D, Polygon2D
from ladybug_geometry.geometry3d import Plane, Mesh3D, Face3D


class THMZResult(object):
    """Object for parsing results out of simulated THMZ files.

    Args:
        file_path: Full path to a THMZ file that was simulated using THERM.

    Properties:
        * file_path
        * u_factors
        * plane
        * shape_polygons
        * shape_faces
        * mesh
        * temperatures
        * humidities
        * water_contents
        * heat_fluxes
        * heat_flux_magnitudes
    """

    def __init__(self, file_path):
        """Initialize THMZResult."""
        assert os.path.isfile(file_path), 'No file was found at {}'.format(file_path)
        assert file_path.lower().endswith('.thmz'), \
            '"{}" is not a THMZ file ending in .thmz.'.format(file_path)
        self._file_path = file_path

        # set up variables to track what has been loaded from the file
        self._plane_loaded = False
        self._mesh_loaded = False
        self._faces_loaded = False
        self._u_factors_loaded = False
        self._ss_mesh_results_loaded = False

        # values to be computed as soon as they are requested
        self._plane = None
        self._translation_vec = None
        self._shape_polygons = None
        self._shape_faces = None
        self._u_factors = None
        self._mesh = None
        self._disconnected_i = None
        self._temperatures = None
        self._humidities = None
        self._water_contents = None
        self._heat_fluxes = None
        self._heat_flux_magnitudes = None

    @property
    def file_path(self):
        """Get the path to the .thmz file."""
        return self._file_path

    @property
    def u_factors(self):
        """Get a tuple of UFactor objects for the .

        This will be None if there is no U-Factor information in the THMZ file
        and this will be an empty tuple if the model had no U-Factor tags assigned
        to it.
        """
        if not self._u_factors_loaded:
            self._extract_u_factors()
        return self._u_factors

    @property
    def plane(self):
        """Get a ladybug-geometry Plane for the 3D plane in which the mesh exists.

        This will be the World XY plane if there is no plane information in the
        THMZ file.
        """
        if not self._plane_loaded:
            self._extract_plane()
        return self._plane

    @property
    def shape_polygons(self):
        """Get a ladybug-geometry Polygon2Ds for the Shape geometries in the THMZ file.
        """
        if not self._plane_loaded:
            self._extract_plane()
        return self._shape_polygons

    @property
    def shape_faces(self):
        """Get a ladybug-geometry Face3Ds for the Shape geometries in the THMZ file.
        """
        if not self._faces_loaded:
            self._extract_faces()
        return self._shape_faces

    @property
    def mesh(self):
        """Get a ladybug-geometry Mesh3D for the finite element mesh of the model.

        Will be None if the THMZ file has not been simulated and there is no Mesh
        in the file.
        """
        if not self._mesh_loaded:
            self._extract_mesh()
        return self._mesh

    @property
    def temperatures(self):
        """Get a tuple of temperatures in Celsius that correspond to the mesh vertices.

        Will be None if the THMZ file has not been simulated and there are no
        steady state results in the file.
        """
        if not self._ss_mesh_results_loaded:
            self._extract_steady_state_results()
        return self._temperatures

    @property
    def humidities(self):
        """Get a tuple of relative humidities [0,1] matching the mesh vertices.

        Nodes are reported in the same order as temperatures. Entries are
        None for nodes without a humidity result and the whole tuple is
        None when the file holds no humidity field (dry steady results or
        an unsimulated file).
        """
        if not self._ss_mesh_results_loaded:
            self._extract_steady_state_results()
        return self._humidities

    @property
    def water_contents(self):
        """Get a tuple of water contents [kg/m3] matching the mesh vertices.

        Nodes are reported in the same order as temperatures. Entries are
        None for nodes without a water content result and the whole tuple
        is None when the file holds no water content field.
        """
        if not self._ss_mesh_results_loaded:
            self._extract_steady_state_results()
        return self._water_contents

    @property
    def heat_fluxes(self):
        """Get a tuple of Vector2Ds that correspond to the mesh vertices for heat fluxes.

        Will be None if the THMZ file has not been simulated and there are no
        steady state results in the file.
        """
        if not self._ss_mesh_results_loaded:
            self._extract_steady_state_results()
        return self._heat_fluxes

    @property
    def heat_flux_magnitudes(self):
        """Get a tuple of heat flux values in W/m2 in that correspond to mesh vertices.

        Will be None if the THMZ file has not been simulated and there are no
        steady state results in the file.
        """
        if not self._ss_mesh_results_loaded:
            self._extract_steady_state_results()
        return self._heat_flux_magnitudes

    def _extract_u_factors(self):
        """Extract U-factor results from the THMZ file."""
        self._u_factors_loaded = True
        try:  # load the root of the SteadyStateResults.xml
            with zipfile.ZipFile(self.file_path, 'r') as archive:
                with archive.open('SteadyStateResults.xml') as f:
                    content = f.read()
        except KeyError:  # no results in the file; it has not been simulated
            return
        # extract the temperatures and heat fluxes from the model
        xml_root = ET.fromstring(content)
        xml_case = xml_root.find('Case')
        u_factors = []
        for xml_u_fac in xml_case:
            if xml_u_fac.tag == 'U-factors':
                u_factors.append(UFactor(xml_u_fac))
        self._u_factors = tuple(u_factors)

    def _extract_plane(self):
        """Extract a Plane object and Polygons from the THMZ file."""
        self._plane_loaded = True
        # load the root of the Model.xml
        with zipfile.ZipFile(self.file_path, 'r') as archive:
            with archive.open('Model.xml') as f:
                content = f.read()
        xml_root = ET.fromstring(content)
        # extract the Plane specification form the model
        xml_props = xml_root.find('Properties')
        xml_gen = xml_props.find('General')
        xml_notes = xml_gen.find('Notes')
        all_notes = xml_notes.text
        if all_notes is not None:
            _plane_pattern = re.compile(r"Plane:\s(.*)")
            matches = _plane_pattern.findall(all_notes)
            if len(matches) > 0:
                self._plane = Plane.from_dict(json.loads(matches[0]))
            else:
                self._plane = Plane()
        else:
            self._plane = Plane()
        # extract the shape geometries as Polygon2Ds
        shape_geos = []
        xml_shapes = xml_root.find('Polygons')
        for xml_shape in xml_shapes:
            vertices = []
            for xpt in xml_shape.find('Points'):
                vertices.append(Point2D(xpt.find('x').text, xpt.find('y').text))
            shape_geos.append(Polygon2D(vertices))
        self._shape_polygons = tuple(shape_geos)
        # extract the translation vector from the glazing origin
        xml_origin = xml_root.find('GlazingOrigin')
        xml_o_x = xml_origin.find('x')
        xml_o_y = xml_origin.find('y')
        self._translation_vec = Vector2D(float(xml_o_x.text), float(xml_o_y.text))

    def _extract_mesh(self):
        """Extract a Mesh3D object from the THMZ file."""
        self._mesh_loaded = True
        try:  # load the root of the Mesh.xml
            with zipfile.ZipFile(self.file_path, 'r') as archive:
                with archive.open('Mesh.xml') as f:
                    content = f.read()
        except KeyError:  # no mesh in the file; it has not been simulated
            return
        # get the mesh information from the root
        xml_root = ET.fromstring(content)
        xml_case = xml_root.find('Case')
        # extract the vertices (aka. nodes) from the model
        plane = self.plane
        vertices_2d = []
        for xml_node in xml_case.find('Nodes'):
            pt_2d = Point2D(
                float(xml_node.find('x').text) * 1000,
                float(xml_node.find('y').text) * 1000
            )  # convert from meters back to mm
            vertices_2d.append(pt_2d)
        # move the vertices to be in 3D Fairyfly-Next space instead of 2D THERM space
        vertices = []
        for pt2 in vertices_2d:
            vertices.append(plane.xy_to_xyz(pt2.move(self._translation_vec)))
        # extract the faces (aka. elements) from the model
        faces, pt_set = [], set()
        for xml_face in xml_case.find('Elements'):
            face_i = []
            for e_prop in xml_face:
                if e_prop.tag.startswith('node'):
                    fi = int(e_prop.text)
                    face_i.append(fi)
                    pt_set.add(fi)
            faces.append(tuple(face_i))
        # remove any vertices that do not connect to a face
        self._disconnected_i = []
        for i in range(len(vertices)):
            if i not in pt_set:
                self._disconnected_i.append(i)
        self._disconnected_i = list(reversed(self._disconnected_i))
        for ri in self._disconnected_i:
            vertices.pop(ri)
        self._mesh = Mesh3D(vertices, faces)

    def _extract_faces(self):
        """Extract Face3D object from the THMZ file."""
        self._faces_loaded = True
        polygons, plane = self.shape_polygons, self.plane
        faces = []
        for polygon in polygons:
            vertices = [plane.xy_to_xyz(pt2) for pt2 in polygon]
            faces.append(Face3D(vertices, plane))
        self._shape_faces = tuple(faces)

    def _extract_steady_state_results(self):
        """Extract steady state results from the THMZ file."""
        self.mesh  # extract the mesh to coordinate results
        self._ss_mesh_results_loaded = True
        try:  # load the root of the SteadyStateMeshResults.xml
            with zipfile.ZipFile(self.file_path, 'r') as archive:
                with archive.open('SteadyStateMeshResults.xml') as f:
                    content = f.read()
        except KeyError:  # no results in the file; it has not been simulated
            return
        # extract the temperatures and heat fluxes from the model
        xml_root = ET.fromstring(content)
        xml_case = xml_root.find('Case')
        temperatures, humidities, water_contents = [], [], []
        heat_fluxes, flux_magnitudes = [], []
        for xml_node in xml_case.find('Nodes'):
            temperatures.append(float(xml_node.find('Temperature').text))
            vec_2d = Vector2D(xml_node.find('X-flux').text, xml_node.find('Y-flux').text)
            heat_fluxes.append(vec_2d)
            flux_magnitudes.append(vec_2d.magnitude)
            # Humidity and WaterContent are optional node fields written by
            # hygrothermal solves; absent values stay None per node
            text = xml_node.findtext('Humidity')
            humidities.append(None if text is None else float(text))
            text = xml_node.findtext('WaterContent')
            water_contents.append(None if text is None else float(text))
        # remove the last two vertices (I don't know where they come from)
        for res_list in (temperatures, humidities, water_contents,
                         heat_fluxes, flux_magnitudes):
            for ri in self._disconnected_i:
                res_list.pop(ri)
        self._temperatures = tuple(temperatures)
        if any(value is not None for value in humidities):
            self._humidities = tuple(humidities)
        if any(value is not None for value in water_contents):
            self._water_contents = tuple(water_contents)
        self._heat_fluxes = tuple(heat_fluxes)
        self._heat_flux_magnitudes = tuple(flux_magnitudes)

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'THMZ Result: {}'.format(self.file_path)


class UFactor(object):
    """Object for holding the results of an individual U-factor tag.

    Args:
        xml_element: An XML element for a U-factor result in the
            SteadyStateResults.xml file.

    Properties:
        * name
        * delta_temperature
        * heat_flux
        * total_u_factor
        * total_length
        * projected_x_u_factor
        * projected_x_length
        * projected_y_u_factor
        * projected_y_length
        * projected_in_glass_plane_u_factor
        * projected_in_glass_plane_length
        * custom_rotation_u_factor
        * custom_rotation_length
    """

    __slots__ = (
        '_name', '_delta_temperature', '_heat_flux', '_total_u_factor', '_total_length',
        '_projected_x_u_factor', '_projected_x_length',
        '_projected_y_u_factor', '_projected_y_length',
        '_projected_in_glass_plane_u_factor', '_projected_in_glass_plane_length',
        '_custom_rotation_u_factor', '_custom_rotation_length')

    def __init__(self, xml_element):
        """Initialize UFactor."""
        # get the basic properties like the name and heat flux
        self._name = xml_element.find('Tag').text
        self._delta_temperature = float(xml_element.find('DeltaT').text)
        self._heat_flux = float(xml_element.find('HeatFlux').text)

        # set defaults for the different U-factors in case they are not found
        self._total_u_factor = None
        self._total_length = 0
        self._projected_x_u_factor = None
        self._projected_x_length = 0
        self._projected_y_u_factor = None
        self._projected_y_length = 0
        self._projected_in_glass_plane_u_factor = None
        self._projected_in_glass_plane_length = 0
        self._custom_rotation_u_factor = None
        self._custom_rotation_length = 0

        # extract the different types of U-factors
        for xml_project in xml_element:
            if xml_project.tag == 'Projection':
                len_type = xml_project.find('Length-type').text
                if len_type == 'Total Length':
                    self._set_u_factors(
                        xml_project, '_total_u_factor', '_total_length')
                elif len_type == 'Projected X':
                    self._set_u_factors(
                        xml_project, '_projected_x_u_factor', '_projected_x_length')
                elif len_type == 'Projected Y':
                    self._set_u_factors(
                        xml_project, '_projected_y_u_factor', '_projected_y_length')
                elif len_type == 'Projected in glass plane':
                    self._set_u_factors(
                        xml_project, '_projected_in_glass_plane_u_factor',
                        '_projected_in_glass_plane_length')
                elif len_type == 'Custom Rotation':
                    self._set_u_factors(
                        xml_project, '_custom_rotation_u_factor',
                        '_custom_rotation_length')

    @property
    def name(self):
        """Get the name of the U-factor tag."""
        return self._name

    @property
    def delta_temperature(self):
        """Get a number for the temperature delta across the boundaries in Celsius."""
        return self._delta_temperature

    @property
    def heat_flux(self):
        """Get boundary-integrated heat flux in W/m of model depth."""
        return self._heat_flux

    @property
    def total_u_factor(self):
        """Get a number for the total U-Factor across the boundaries in W/m2-K."""
        return self._total_u_factor

    @property
    def total_length(self):
        """Get a number for the total length the boundaries in mm."""
        return self._total_length

    @property
    def projected_x_u_factor(self):
        """Get a number for the X-projected U-Factor across the boundaries in W/m2-K."""
        return self._projected_x_u_factor

    @property
    def projected_x_length(self):
        """Get a number for the X-projected length the boundaries in mm."""
        return self._projected_x_length

    @property
    def projected_y_u_factor(self):
        """Get a number for the X-projected U-Factor across the boundaries in W/m2-K."""
        return self._projected_y_u_factor

    @property
    def projected_y_length(self):
        """Get a number for the Y-projected length the boundaries in mm."""
        return self._projected_y_length

    @property
    def projected_in_glass_plane_u_factor(self):
        """Get a number for the glass plane-projected U-Factor in W/m2-K."""
        return self._projected_in_glass_plane_u_factor

    @property
    def projected_in_glass_plane_length(self):
        """Get a number for the glass plane-projected length in mm."""
        return self._projected_in_glass_plane_length

    @property
    def custom_rotation_u_factor(self):
        """Get a number for the custom rotation-projected U-Factor in W/m2-K."""
        return self._custom_rotation_u_factor

    @property
    def custom_rotation_length(self):
        """Get a number for the custom rotation-projected length in mm."""
        return self._custom_rotation_length

    def _set_u_factors(self, xml_project, u_fac_attr, len_attr):
        """Set the U-Factor properties given an XML Projection element."""
        xml_len = xml_project.find('Length')
        length = None
        if xml_len is not None:
            length = float(xml_len.text)
            setattr(self, len_attr, length)
        xml_u_fac = xml_project.find('U-factor')
        if xml_u_fac is not None and self.delta_temperature != 0 and \
                length is not None and length > 0:
            setattr(self, u_fac_attr, float(xml_u_fac.text))

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __repr__(self):
        return 'UFactor: {}'.format(self.name)
