# coding=utf-8
"""Meshing control parameters."""
from __future__ import division
import xml.etree.ElementTree as ET

from fairyfly.typing import float_in_range, int_positive


class MeshControl(object):
    """Meshing control parameters.

    Args:
        mesh_type: Legacy THERM selector. Rhino always uses QuadRemeshBrep,
            regardless of this value. (Default: Simmetrix).

            * Simmetrix
            * QuadTree

        parameter: Rhino TargetQuadCount for native meshing. The actual Q4 count
            may differ. (Default: 20).
        run_error_estimator: Check solved global recovered-flux energy error and
            globally refine the Rhino mesh if needed. (Default: True).
        max_error_percent: Maximum global energy error, calculated as 100 times
            sqrt(error energy / (FE energy + error energy)). (Default: 10).
        max_iterations: Maximum number of native mesh/solve passes. (Default: 5).

    Properties:
        * mesh_type
        * parameter
        * run_error_estimator
        * max_error_percent
        * max_iterations
    """
    __slots__ = ('_mesh_type', '_parameter', '_run_error_estimator',
                 '_max_error_percent', '_max_iterations')
    TYPES = ('Simmetrix', 'QuadTree')

    def __init__(self, mesh_type='Simmetrix', parameter=20, run_error_estimator=True,
                 max_error_percent=10, max_iterations=5):
        """Initialize MeshControl."""
        self.mesh_type = mesh_type
        self.parameter = parameter
        self.run_error_estimator = run_error_estimator
        self.max_error_percent = max_error_percent
        self.max_iterations = max_iterations

    @property
    def mesh_type(self):
        """Get or set text for the meshing algorithm to be used."""
        return self._mesh_type

    @mesh_type.setter
    def mesh_type(self, value):
        if value is not None:
            clean_input = str(value).lower()
            for key in self.TYPES:
                if key.lower() == clean_input:
                    value = key
                    break
            else:
                raise ValueError(
                    'Mesh control mesh_type "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.TYPES)))
            self._mesh_type = value
        else:
            self._mesh_type = self.TYPES[0]

    @property
    def parameter(self):
        """Get or set a positive integer for the minimum number of mesh subdivisions."""
        return self._parameter

    @parameter.setter
    def parameter(self, value):
        self._parameter = int_positive(value, 'MeshControl parameter')
        assert self._parameter > 1, 'MeshControl parameter must be greater than 1.'

    @property
    def run_error_estimator(self):
        """Get or set a boolean for whether to run the error estimator."""
        return self._run_error_estimator

    @run_error_estimator.setter
    def run_error_estimator(self, value):
        self._run_error_estimator = bool(value)

    @property
    def max_error_percent(self):
        """Get or set a number for the maximum accepted percentage of error."""
        return self._max_error_percent

    @max_error_percent.setter
    def max_error_percent(self, value):
        self._max_error_percent = \
            float_in_range(value, 0, 100, 'MeshControl error percent')

    @property
    def max_iterations(self):
        """Get or set a positive integer for the iterations between the mesher and solver.
        """
        return self._max_iterations

    @max_iterations.setter
    def max_iterations(self, value):
        self._max_iterations = int_positive(value, 'MeshControl max iterations')

    @classmethod
    def from_therm_xml(cls, xml_element):
        """Create MeshControl from an XML element of a THERM MeshControl.

        Args:
            xml_element: An XML element of a THERM MeshControl.
        """
        xml_type = xml_element.find('MeshType')
        mesh_type = 'Simmetrix' \
            if xml_type.text == 'Simmetrix Version 2022' else 'QuadTree'
        xml_param = xml_element.find('MeshParameter')
        xml_run = xml_element.find('RunErrorEstimator')
        run_err = True if xml_run.text == 'true' else False
        xml_error = xml_element.find('ErrorEnergyNorm')
        xml_iter = xml_element.find('MaximumIterations')
        return MeshControl(mesh_type, xml_param.text, run_err,
                           xml_error.text, xml_iter.text)

    @classmethod
    def from_therm_xml_str(cls, xml_str):
        """Create a MeshControl from an XML text string of a THERM MeshControl.

        Args:
            xml_str: An XML text string of a THERM MeshControl.
        """
        root = ET.fromstring(xml_str)
        return cls.from_therm_xml(root)

    @classmethod
    def from_dict(cls, data):
        """Create a MeshControl from a dictionary.

        Args:
            data: A python dictionary in the following format

        .. code-block:: python

            {
            "type": 'MeshControl',
            "mesh_type": 'Simmetrix',
            "parameter": 50,
            "run_error_estimator": True,
            "max_error_percent": 10,
            "max_iterations": 5
            }
        """
        assert data['type'] == 'MeshControl', \
            'Expected MeshControl. Got {}.'.format(data['type'])
        type = data['mesh_type'] if 'mesh_type' in data and \
            data['mesh_type'] is not None else 'Simmetrix'
        param = data['parameter'] if 'parameter' in data else 20
        run = data['run_error_estimator'] if 'run_error_estimator' in data else True
        error = data['max_error_percent'] if 'max_error_percent' in data else 10
        iter = data['max_iterations'] if 'max_iterations' in data else 5
        return cls(type, param, run, error, iter)

    def to_therm_xml(self, calculation_element=None):
        """Get an THERM XML element of the MeshControl.

        Args:
            calculation_element: An optional XML Element for the CalculationOptions to
                which the generated objects will be added. If None, a new XML
                Element will be generated.

        .. code-block:: xml

            <MeshControl>
                <MeshType>QuadTree Mesher</MeshType>
                <MeshParameter>3</MeshParameter>
                <RunErrorEstimator>true</RunErrorEstimator>
                <ErrorEnergyNorm>10</ErrorEnergyNorm>
                <MaximumIterations>5</MaximumIterations>
            </MeshControl>
        """
        # create a new Materials element if one is not specified
        if calculation_element is not None:
            xml_mesh = ET.SubElement(calculation_element, 'MeshControl')
        else:
            xml_mesh = ET.Element('MeshControl')
        # add all of the required basic attributes
        xml_type = ET.SubElement(xml_mesh, 'MeshType')
        xml_type.text = 'Simmetrix Version 2022' \
            if self.mesh_type == 'Simmetrix' else 'QuadTree Mesher'
        xml_param = ET.SubElement(xml_mesh, 'MeshParameter')
        xml_param.text = str(self.parameter)
        xml_run = ET.SubElement(xml_mesh, 'RunErrorEstimator')
        xml_run.text = 'true' if self.run_error_estimator else 'false'
        xml_error = ET.SubElement(xml_mesh, 'ErrorEnergyNorm')
        xml_error.text = str(self.max_error_percent)
        xml_iter = ET.SubElement(xml_mesh, 'MaximumIterations')
        xml_iter.text = str(self.max_iterations)
        return xml_mesh

    def to_therm_xml_str(self):
        """Get an THERM XML string of the material."""
        xml_root = self.to_therm_xml()
        try:  # try to indent the XML to make it read-able
            ET.indent(xml_root)
            return ET.tostring(xml_root, encoding='unicode')
        except AttributeError:  # we are in Python 2 and no indent is available
            return ET.tostring(xml_root)

    def to_dict(self):
        """MeshControl dictionary representation."""
        base = {
            'type': 'MeshControl',
            'mesh_type': self.mesh_type,
            'parameter': self.parameter,
            'run_error_estimator': self.run_error_estimator,
            'max_error_percent': self.max_error_percent,
            'max_iterations': self.max_iterations
        }
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.mesh_type, self.parameter, self.run_error_estimator,
                self.max_error_percent, self.max_iterations)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, MeshControl) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return self.__class__(
            self.mesh_type, self.parameter, self.run_error_estimator,
            self.max_error_percent, self.max_iterations)

    def __repr__(self):
        return 'MeshControl: {} - Parameter {}'.format(self.mesh_type, self.parameter)
