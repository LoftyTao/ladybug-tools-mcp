# coding=utf-8
"""Model exposure parameters."""
from __future__ import division
import math
import xml.etree.ElementTree as ET

from ladybug_geometry.geometry3d import Vector3D

from fairyfly.typing import float_in_range


class ModelExposure(object):
    """Model exposure parameters.

    Args:
        model_type: Text to indicate the type of construction detail or the purpose
            of the model. Chose from the following. (Default: Other).

            * Window
            * Opaque Wall
            * Opaque Roof
            * Other

        cross_section_type: Text to indicate the type of cross section that the
            model represents. The acceptable fields here depend upon the model_type.
            If None, the default is set to the top of each list below for each model_type.
            For the Window model_type, choose from the following.

            * Sill
            * Jamb
            * Head
            * Horizontal Divider
            * Vertical Divider
            * Horizontal Meeting Rail
            * Vertical Meeting Rail
            * Common Frame
            * Spacer

            For the Opaque Wall and Roof model_type, choose from the following.

            * Sill Plate
            * Header
            * End Section
            * Middle Section
            * Thermal Bridge
            * Window Framing - Sill
            * Rough Opening - Header
            * Rough Opening - Jamb

            For the Other model_type, choose from the following.

            * General Cross Section
            * Common Thermal Bridge

        gravity_orientation: Text to indicate the direction of gravity for the model.
            If None, this will be computed from the orientation of the model plane
            in the 3D scene. (Default: None).

            * Down
            * Up
            * Left
            * Right
            * Into Screen
            * Out Of Screen

        wind_orientation: A number between 0 and 360 for the direction the exterior
            surface of the model faces. This orientation of the exterior surface
            is used to determine the wind direction for the simulation.
            For reference, 0 = North, 90 = East, 180 = South, 270 = West. (Default: 0).

    Properties:
        * model_type
        * cross_section_type
        * gravity_orientation
        * wind_orientation
    """
    __slots__ = ('_model_type', '_cross_section_type', '_gravity_orientation',
                 '_wind_orientation')
    MODEL_TYPES = ('Window', 'Opaque Wall', 'Opaque Roof', 'Other')
    WINDOW_SECTIONS = (
        'Sill', 'Jamb', 'Head', 'Horizontal Divider', 'Vertical Divider',
        'Horizontal Meeting Rail', 'Vertical Meeting Rail', 'Common Frame', 'Spacer'
    )
    OPAQUE_SECTIONS = (
        'Sill Plate', 'Header', 'End Section', 'Middle Section', 'Thermal Bridge',
        'Window Framing - Sill', 'Rough Opening - Header', 'Rough Opening - Jamb'
    )
    OTHER_SECTIONS = (
        'General Cross Section', 'Common Thermal Bridge',
    )
    ALL_SECTIONS = WINDOW_SECTIONS + OPAQUE_SECTIONS + OTHER_SECTIONS
    GRAVITY_ORIENTATIONS = (
        'Down', 'Up', 'Left', 'Right', 'Into Screen', 'Out Of Screen'
    )
    SECTION_MAP = {
        'Window': WINDOW_SECTIONS[0],
        'Opaque Wall': OPAQUE_SECTIONS[0],
        'Opaque Roof': OPAQUE_SECTIONS[0],
        'Other': OTHER_SECTIONS[0],
    }

    def __init__(self, model_type='Other', cross_section_type=None,
                 gravity_orientation=None, wind_orientation=0):
        """Initialize ModelExposure."""
        self._cross_section_type = None  # default so that init can proceed
        self._gravity_orientation = None  # default so that init can proceed

        self.model_type = model_type
        self.cross_section_type = cross_section_type
        self.gravity_orientation = gravity_orientation
        self.wind_orientation = wind_orientation

    @property
    def model_type(self):
        """Get or set text for the type of construction detail."""
        return self._model_type

    @model_type.setter
    def model_type(self, value):
        if value is not None:
            clean_input = str(value).lower()
            for key in self.MODEL_TYPES:
                if key.lower() == clean_input:
                    value = key
                    break
            else:
                raise ValueError(
                    'ModelExposure model_type "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.MODEL_TYPES)))
            self._model_type = value
        else:
            self._model_type = 'Other'
        self._check_model_and_cross_section()

    @property
    def cross_section_type(self):
        """Get or set text for the type of cross section."""
        return self._cross_section_type if self._cross_section_type is not None \
            else self.SECTION_MAP[self._model_type]

    @cross_section_type.setter
    def cross_section_type(self, value):
        if value is not None:
            clean_input = str(value).lower()
            for key in self.ALL_SECTIONS:
                if key.lower() == clean_input:
                    value = key
                    break
            else:
                raise ValueError(
                    'ModelExposure cross_section_type "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.ALL_SECTIONS)))
        self._cross_section_type = value
        self._check_model_and_cross_section()

    @property
    def gravity_orientation(self):
        """Get or set text for the direction of gravity for the model."""
        return self._gravity_orientation

    @gravity_orientation.setter
    def gravity_orientation(self, value):
        if value is not None:
            clean_input = str(value).lower()
            for key in self.GRAVITY_ORIENTATIONS:
                if key.lower() == clean_input:
                    value = key
                    break
            else:
                raise ValueError(
                    'ModelExposure gravity_orientation "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.GRAVITY_ORIENTATIONS)))
        self._gravity_orientation = value

    @property
    def wind_orientation(self):
        """Get or set a number for the direction the exterior surface of the model faces.
        """
        return self._wind_orientation

    @wind_orientation.setter
    def wind_orientation(self, value):
        self._wind_orientation = \
            float_in_range(value, 0, 360, 'ModelExposure wind orientation')

    def _check_model_and_cross_section(self):
        """Check to be sure that the model and cross section type are compatible."""
        # set up the base message templates
        msg_init = 'Cross section type "{}" is not supported for model ' \
            'type "{}".'.format(self.cross_section_type, self.model_type)
        msg_template = '{}\nChoose from the following:\n{}'
        # perform the checks on the inputs
        if self.cross_section_type is None:
            return  # using None will always be supported
        if self.model_type == 'Other':
            assert self.cross_section_type in self.OTHER_SECTIONS, \
                msg_template.format(msg_init, '\n'.join(self.OTHER_SECTIONS))
        elif self.model_type == 'Window':
            assert self.cross_section_type in self.WINDOW_SECTIONS, \
                msg_template.format(msg_init, '\n'.join(self.WINDOW_SECTIONS))
        else:
            assert self.cross_section_type in self.OPAQUE_SECTIONS, \
                msg_template.format(msg_init, '\n'.join(self.OPAQUE_SECTIONS))

    @classmethod
    def from_therm_xml(cls, xml_element):
        """Create ModelExposure from an XML element of a THERM ModelExposure.

        Args:
            xml_element: An XML element of a THERM ModelExposure.
        """
        xml_exp = xml_element.find('Exposure')
        purpose = xml_exp.find('ModelPurpose').text
        if purpose == 'Other':
            model_type = 'Other'
            cross_type = xml_exp.find('OtherCrossSection').text
        elif purpose == 'Window/Transparent Facade':
            model_type = 'Window'
            cross_type = xml_exp.find('WindowCrossSection').text
        else:
            model_type = 'Opaque {}'.format(xml_exp.find('Assembly').text)
            cross_type = xml_exp.find('OpaqueCrossSection').text
        xml_g_orient = xml_element.find('GravityOrientation')
        xml_w_orient = xml_element.find('ModelOrientation')
        return ModelExposure(
            model_type, cross_type, xml_g_orient.text, xml_w_orient.text)

    @classmethod
    def from_therm_xml_str(cls, xml_str):
        """Create a ModelExposure from an XML text string of a THERM ModelExposure.

        Args:
            xml_str: An XML text string of a THERM ModelExposure.
        """
        root = ET.fromstring(xml_str)
        return cls.from_therm_xml(root)

    @classmethod
    def from_dict(cls, data):
        """Create a ModelExposure from a dictionary.

        Args:
            data: A python dictionary in the following format

        .. code-block:: python

            {
            "type": 'ModelExposure',
            "model_type": 'Window',
            "cross_section_type": 'Sill',
            "gravity_orientation": 'Down',
            "wind_orientation": 0
            }
        """
        assert data['type'] == 'ModelExposure', \
            'Expected ModelExposure. Got {}.'.format(data['type'])
        m_type = data['model_type'] if 'model_type' in data and \
            data['model_type'] is not None else 'Other'
        c_type = data['cross_section_type'] if 'cross_section_type' in data and \
            data['cross_section_type'] is not None else None
        g_orient = data['gravity_orientation'] if 'gravity_orientation' in data and \
            data['gravity_orientation'] is not None else None
        w_orient = data['wind_orientation'] if 'wind_orientation' in data else 0
        return cls(m_type, c_type, g_orient, w_orient)

    def to_therm_xml(self, properties_element=None, model_plane=None):
        """Get an THERM XML element of the ModelExposure.

        Args:
            properties_element: An optional XML Element for the ThermModel Properties to
                which the generated objects will be added. If None, a new XML
                Element will be generated. (Default: None).
            model_plane: An optional ladybug-geometry Plane object noting the
                orientation of the model in 3D space. This will be used to set
                the default gravity orientation if none has been specified
                here. (Default: None).

        .. code-block:: xml

            <ModelExposure>
                <ModelOrientation>0</ModelOrientation>
                <GravityOrientation>Down</GravityOrientation>
                <Exposure>
                    <ModelPurpose>Window/Transparent Facade</ModelPurpose>
                    <WindowCrossSection>Sill</WindowCrossSection>
                </Exposure>
            </ModelExposure>
        """
        # create a new Materials element if one is not specified
        if properties_element is not None:
            xml_exp = ET.SubElement(properties_element, 'ModelExposure')
        else:
            xml_exp = ET.Element('ModelExposure')
        # set the wind and gravity orientation
        xml_w_ornt = ET.SubElement(xml_exp, 'ModelOrientation')
        xml_w_ornt.text = str(self.wind_orientation)
        xml_g_ornt = ET.SubElement(xml_exp, 'GravityOrientation')
        if self.gravity_orientation is None:
            if model_plane is not None:
                plane_vec = model_plane.n if model_plane.n.z >= 0 else \
                    model_plane.n.reverse()
                up_ang = plane_vec.angle(Vector3D(0, 0, 1))
                xml_g_ornt.text = 'Into Screen' if math.degrees(up_ang) < 45 else 'Down'
            else:
                xml_g_ornt.text = 'Down'
        else:
            xml_g_ornt.text = self.gravity_orientation
        # set the model and cross-section types
        xml_e = ET.SubElement(xml_exp, 'Exposure')
        xml_mp = ET.SubElement(xml_e, 'ModelPurpose')
        if self.model_type == 'Window':
            xml_mp.text = 'Window/Transparent Facade'
            xml_cs = ET.SubElement(xml_e, 'WindowCrossSection')
        elif self.model_type == 'Opaque Wall':
            xml_mp.text = 'Opaque Facade'
            xml_at = ET.SubElement(xml_e, 'Assembly')
            xml_at.text = 'Walls'
            xml_cs = ET.SubElement(xml_e, 'OpaqueCrossSection')
        elif self.model_type == 'Opaque Roof':
            xml_mp.text = 'Opaque Facade'
            xml_at = ET.SubElement(xml_e, 'Assembly')
            xml_at.text = 'Roof'
            xml_cs = ET.SubElement(xml_e, 'OpaqueCrossSection')
        else:
            xml_mp.text = self.model_type
            xml_cs = ET.SubElement(xml_e, 'OtherCrossSection')
        xml_cs.text = self.cross_section_type
        return xml_exp

    def to_therm_xml_str(self):
        """Get an THERM XML string of the material."""
        xml_root = self.to_therm_xml()
        try:  # try to indent the XML to make it read-able
            ET.indent(xml_root)
            return ET.tostring(xml_root, encoding='unicode')
        except AttributeError:  # we are in Python 2 and no indent is available
            return ET.tostring(xml_root)

    def to_dict(self):
        """ModelExposure dictionary representation."""
        base = {
            'type': 'ModelExposure',
            'model_type': self.model_type,
            'wind_orientation': self.wind_orientation
        }
        if self._cross_section_type is not None:
            base['cross_section_type'] = self.cross_section_type
        if self._gravity_orientation is not None:
            base['gravity_orientation'] = self.gravity_orientation
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self._model_type, self._cross_section_type,
                self._gravity_orientation, self._wind_orientation)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, ModelExposure) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return self.__class__(
            self._model_type, self._cross_section_type, self._gravity_orientation,
            self._wind_orientation)

    def __repr__(self):
        return 'ModelExposure: {} - {}'.format(self.model_type, self.cross_section_type)
