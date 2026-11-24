# coding=utf-8
"""Cavity THERM material."""
from __future__ import division
import xml.etree.ElementTree as ET

from fairyfly._lockable import lockable
from fairyfly.typing import float_in_range, therm_id_from_uuid, uuid_from_therm_id

from ._base import _ThermMaterialBase
from .gas import Gas
from ..lib.gases import air


@lockable
class CavityMaterial(_ThermMaterialBase):
    """Typical cavity material.

    Args:
        gas: A Gas material object for the gas that fills the cavity. (Default: air).
        cavity_model: Text for the type of cavity model to be used to determine
            the thermal resistance of the material. Choose from the following:

            * CEN
            * NFRC
            * ISO15099
            * ISO15099Ventilated

            NFRC denotes the standard nonventilated NFRC 100 frame cavity. It
            exports ISO15099 with Air; choose ISO15099Ventilated for a slightly
            ventilated exterior frame cavity. This is not a certification.

        emissivity: Number between 0 and 1 for the infrared hemispherical
            emissivity of the front side of the material. (Default: 0.9).
        emissivity_back: Number between 0 and 1 for the infrared hemispherical
            emissivity of the back side of the material. If None, this will
            default to the same value specified for emissivity. (Default: None)
        identifier: Text string for a unique object ID. Must be a UUID in the
            format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx. If None, a UUID will
            automatically be generated. (Default: None).

    Properties:
        * identifier
        * display_name
        * therm_uuid
        * gas
        * cavity_model
        * emissivity
        * emissivity_back
        * color
        * protected
        * user_data
    """
    __slots__ = ('_gas', '_cavity_model', '_emissivity', '_emissivity_back')
    CAVITY_MODELS = ('CEN', 'NFRC', 'ISO15099', 'ISO15099Ventilated')

    def __init__(
        self, gas=air, cavity_model='CEN', emissivity=0.9, emissivity_back=None,
        identifier=None
    ):
        """Initialize therm material."""
        _ThermMaterialBase.__init__(self, identifier)
        self.gas = gas
        self.cavity_model = cavity_model
        self.emissivity = emissivity
        self.emissivity_back = emissivity_back

    @property
    def gas(self):
        """Get or set a Gas object used to denote the gas in the cavity."""
        return self._gas

    @gas.setter
    def gas(self, value):
        if value is not None:
            assert isinstance(value, Gas), 'Expected Gas object for CavityMaterial ' \
                'gas. Got {}.'.format(type(value))
        else:
            value = air
        self._gas = value

    @property
    def cavity_model(self):
        """Get or set text for the convection model to be used in the cavity."""
        return self._cavity_model

    @cavity_model.setter
    def cavity_model(self, value):
        if value is not None:
            clean_input = str(value).lower()
            for key in self.CAVITY_MODELS:
                if key.lower() == clean_input:
                    value = key
                    break
            else:
                raise ValueError(
                    'Material cavity_model "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.CAVITY_MODELS)))
            self._cavity_model = value
        else:
            self._cavity_model = self.CAVITY_MODELS[0]

    @property
    def emissivity(self):
        """Get or set the hemispherical emissivity of the front side of the material."""
        return self._emissivity

    @emissivity.setter
    def emissivity(self, ir_e):
        ir_e = float_in_range(ir_e, 0.0, 1.0, 'material emissivity')
        self._emissivity = ir_e

    @property
    def emissivity_back(self):
        """Get or set the hemispherical emissivity of the back side of the material."""
        return self._emissivity_back if self._emissivity_back is not None \
            else self._emissivity

    @emissivity_back.setter
    def emissivity_back(self, ir_e):
        if ir_e is not None:
            ir_e = float_in_range(ir_e, 0.0, 1.0, 'material emissivity')
        self._emissivity_back = ir_e

    @property
    def therm_uuid(self):
        """Get the UUID of this object as it would appear in a THERM XML or thmz file.

        This is always derived from the object identifier but this is slightly
        different than standard UUIDs, which have 4 more values in a 8-4-4-4-12
        structure instead of a 8-4-4-12 structure used by THERM.
        """
        return therm_id_from_uuid(self._identifier)

    @classmethod
    def from_therm_xml(cls, xml_element, gases):
        """Create a CavityMaterial from an XML element of a THERM Material.

        Args:
            xml_element: An XML element of a THERM material.
            gases: A dictionary with gas names as keys and Gas object instances
                as values. These will be used to reassign the gas that fills
                this cavity.
        """
        # create the base material from the UUID and conductivity
        xml_uuid = xml_element.find('UUID')
        identifier = xml_uuid.text
        if len(identifier) == 31:
            identifier = uuid_from_therm_id(identifier)
        xml_cavity = xml_element.find('Cavity')
        xml_c_model = xml_cavity.find('CavityStandard')
        cavity_model = xml_c_model.text
        xml_gas = xml_cavity.find('Gas')
        try:
            gas = gases[xml_gas.text]
        except KeyError as e:
            raise ValueError('Failed to find {} in gases.'.format(e))
        mat = CavityMaterial(gas, cavity_model, identifier=identifier)
        # assign the other attributes if specified
        xml_emiss1 = xml_cavity.find('EmissivitySide1')
        if xml_emiss1 is not None:
            mat.emissivity = xml_emiss1.text
        xml_emiss2 = xml_cavity.find('EmissivitySide2')
        if xml_emiss2 is not None:
            mat.emissivity_back = xml_emiss2.text
        # assign the name and color if they are specified
        xml_name = xml_element.find('Name')
        if xml_name is not None:
            mat.display_name = xml_name.text
        xml_col = xml_element.find('Color')
        if xml_col is not None:
            mat.color = xml_col.text
        xml_protect = xml_element.find('Protected')
        if xml_protect is not None:
            mat.protected = True if xml_protect.text == 'true' else False
        return mat

    @classmethod
    def from_therm_xml_str(cls, xml_str, gases):
        """Create a CavityMaterial from an XML text string of a THERM Material.

        Args:
            xml_str: An XML text string of a THERM material.
            gases: A dictionary with gas names as keys and Gas object instances
                as values. These will be used to reassign the gas that fills
                this cavity.
        """
        root = ET.fromstring(xml_str)
        return cls.from_therm_xml(root, gases)

    @classmethod
    def from_dict(cls, data):
        """Create a CavityMaterial from a dictionary.

        Args:
            data: A python dictionary in the following format

        .. code-block:: python

            {
            "type": 'CavityMaterial',
            "identifier": '0b46bbd7-0dbc-c148-3afe87431bf0',
            "display_name": 'Frame Cavity - CEN Simplified',
            "gas": {},  # dictionary definition of a gas
            "cavity_model": "CEN",
            "emissivity": 0.9,
            "emissivity_back": 0.9
            }
        """
        assert data['type'] == 'CavityMaterial', \
            'Expected CavityMaterial. Got {}.'.format(data['type'])

        emiss = data['emissivity'] if 'emissivity' in data and \
            data['emissivity'] is not None else 0.9
        emiss_b = data['emissivity_back'] if 'emissivity_back' in data else None
        new_mat = cls(
            Gas.from_dict(data['gas']), data['cavity_model'], emiss, emiss_b,
            data['identifier'])
        cls._assign_optional_from_dict(new_mat, data)
        return new_mat

    @classmethod
    def from_dict_abridged(cls, data, gases):
        """Create a Gas from an abridged dictionary.

        Args:
            data: An GasAbridged dictionary.
            gases: A dictionary with Gas identifiers as keys and Gas object instances
                as values. These will be used to reassign the gas that fills
                this cavity.

        .. code-block:: python

            {
            "type": 'CavityMaterial',
            "identifier": '0b46bbd7-0dbc-c148-3afe87431bf0',
            "display_name": 'Frame Cavity - CEN Simplified',
            "gas": '6c2409e9-5296-46c1-be11-9029b59a549b',
            "cavity_model": "CEN",
            "emissivity": 0.9,
            "emissivity_back": 0.9
            }
        """
        assert data['type'] == 'CavityMaterialAbridged', \
            'Expected CavityMaterialAbridged. Got {}.'.format(data['type'])
        try:
            gas_obj = gases[data['gas']]
        except KeyError as e:
            raise ValueError('Failed to find {} in gases.'.format(e))
        emiss = data['emissivity'] if 'emissivity' in data and \
            data['emissivity'] is not None else 0.9
        emiss_b = data['emissivity_back'] if 'emissivity_back' in data else None
        new_mat = cls(gas_obj, data['cavity_model'], emiss, emiss_b, data['identifier'])
        cls._assign_optional_from_dict(new_mat, data)
        return new_mat

    @staticmethod
    def _assign_optional_from_dict(new_obj, data):
        """Assign optional attributes when serializing from dict."""
        if 'display_name' in data and data['display_name'] is not None:
            new_obj.display_name = data['display_name']
        if 'color' in data and data['color'] is not None:
            new_obj.color = data['color']
        if 'protected' in data and data['protected'] is not None:
            new_obj.protected = data['protected']
        if 'user_data' in data and data['user_data'] is not None:
            new_obj.user_data = data['user_data']

    def to_therm_xml(self, materials_element=None):
        """Get an THERM XML element of the material.

        Args:
            materials_element: An optional XML Element for the Materials to
                which the generated objects will be added. If None, a new XML
                Element will be generated.

        .. code-block:: xml

            <Material>
                <UUID>0b46bbd7-0dbc-c148-3afe87431bf0</UUID>
                <Name>Frame Cavity - CEN Simplified</Name>
                <Protected>false</Protected>
                <Color>0xB3FFB3</Color>
                <Cavity>
                    <CavityStandard>CEN</CavityStandard>
                    <Gas>Air</Gas>
                    <EmissivitySide1>0.9</EmissivitySide1>
                    <EmissivitySide2>0.9</EmissivitySide2>
                </Cavity>
            </Material>
        """
        if (self.cavity_model == 'NFRC'
                and (self.gas.display_name != 'Air' or self.gas != air)):
            raise ValueError('NFRC standard cavity requires Air; use ISO15099 '
                             'for other gases')
        # create a new Materials element if one is not specified
        if materials_element is not None:
            xml_mat = ET.SubElement(materials_element, 'Material')
        else:
            xml_mat = ET.Element('Material')
        # add all of the required basic attributes
        xml_id = ET.SubElement(xml_mat, 'UUID')
        xml_id.text = self.therm_uuid
        xml_name = ET.SubElement(xml_mat, 'Name')
        xml_name.text = self.display_name
        xml_protect = ET.SubElement(xml_mat, 'Protected')
        xml_protect.text = 'true' if self.protected else 'false'
        xml_color = ET.SubElement(xml_mat, 'Color')
        xml_color.text = self.color.to_hex().replace('#', '0x')
        xml_cavity = ET.SubElement(xml_mat, 'Cavity')
        # add all of the required cavity attributes
        xml_model = ET.SubElement(xml_cavity, 'CavityStandard')
        # Standard NFRC 100 frame cavities use ISO 15099 in THERM.
        xml_model.text = ('ISO15099' if self.cavity_model == 'NFRC'
                          else self.cavity_model)
        xml_gas = ET.SubElement(xml_cavity, 'Gas')
        xml_gas.text = self.gas.display_name
        xml_emiss = ET.SubElement(xml_cavity, 'EmissivitySide1')
        xml_emiss.text = str(self.emissivity)
        xml_emiss_b = ET.SubElement(xml_cavity, 'EmissivitySide2')
        xml_emiss_b.text = str(self.emissivity_back)
        return xml_mat

    def to_therm_xml_str(self):
        """Get an THERM XML string of the material."""
        xml_root = self.to_therm_xml()
        try:  # try to indent the XML to make it read-able
            ET.indent(xml_root)
            return ET.tostring(xml_root, encoding='unicode')
        except AttributeError:  # we are in Python 2 and no indent is available
            return ET.tostring(xml_root)

    def to_dict(self, abridged=False):
        """CavityMaterial dictionary representation."""
        base = {'type': 'CavityMaterial'} if not abridged \
            else {'type': 'CavityMaterialAbridged'}
        base['identifier'] = self.identifier
        base['gas'] = self.gas.identifier if abridged else self.gas.to_dict()
        base['cavity_model'] = self.cavity_model
        base['emissivity'] = self.emissivity
        if self._emissivity_back is not None:
            base['emissivity_back'] = self.emissivity_back
        if self._display_name is not None:
            base['display_name'] = self.display_name
        base['protected'] = self._protected
        base['color'] = self.color.to_hex()
        if self._user_data is not None:
            base['user_data'] = self.user_data
        return base

    def lock(self):
        """The lock() method will also lock the gas."""
        self._locked = True
        self.gas.lock()

    def unlock(self):
        """The unlock() method will also unlock the gas."""
        self._locked = False
        self.gas.unlock()

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.therm_uuid, hash(self.gas), self.cavity_model,
                self.emissivity, self.emissivity_back)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, CavityMaterial) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        new_material = self.__class__(
            self.gas.duplicate(), self.cavity_model,
            self._emissivity, self._emissivity_back, self.identifier)
        new_material._display_name = self._display_name
        new_material._color = self._color
        new_material._protected = self._protected
        new_material._user_data = None if self._user_data is None \
            else self._user_data.copy()
        return new_material

    def __repr__(self):
        return 'Cavity THERM Material: {}'.format(self.display_name)
