# coding=utf-8
"""SteadyState THERM condition."""
from __future__ import division
import xml.etree.ElementTree as ET

from fairyfly._lockable import lockable
from fairyfly.typing import float_in_range, float_positive, uuid_from_therm_id

from ._base import _ThermConditionBase


@lockable
class SteadyState(_ThermConditionBase):
    """Typical steady state condition.

    Args:
        temperature: A number for the temperature at the boundary in degrees Celsius.
            For NFRC conditions, this temperature should be 21C for interior
            boundary conditions and -18 C for winter exterior boundary conditions.
        film_coefficient: A number in W/m2-K that represents the convective
            resistance of the air film at the boundary condition. Typical film
            coefficient values range from 36 W/m2-K (for an exterior condition
            where outdoor wind strips away most convective resistance) to 2.5 W/m2-K
            (for a vertically-oriented interior wood/vinyl surface). For NFRC
            conditions, this should be 26 for exterior boundary conditions and
            around 3 for interior boundary conditions.
        emissivity: An optional number between 0 and 1 to set the emissivity
            along the boundary, which represents the emissivity of the
            environment to which the material in contact with the boundary is
            radiating to. (Default: 1).
        radiant_temperature: A number for the radiant temperature at the boundary
            in degrees Celsius. If None, this will be the same as the specified
            temperature. (Default: None).
        heat_flux: An optional number in W/m2 that represents additional energy
            flux across the boundary. This can be used to account for solar flux
            among other forms of heat flux. (Default: 0).
        relative_humidity: An optional value between 0 and 1 for the relative
            humidity along the boundary. (Default: 0.5).
        identifier: Text string for a unique object ID. Must be a UUID in the
            format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx. If None, a UUID will
            automatically be generated. (Default: None).

    Properties:
        * identifier
        * display_name
        * temperature
        * film_coefficient
        * emissivity
        * radiant_temperature
        * heat_flux
        * relative_humidity
        * color
        * protected
        * project_tag
        * user_data
    """
    __slots__ = ('_temperature', '_film_coefficient', '_emissivity',
                 '_radiant_temperature', '_heat_flux', '_relative_humidity')

    def __init__(
        self, temperature, film_coefficient, emissivity=1.0, radiant_temperature=None,
        heat_flux=0, relative_humidity=0.5, identifier=None
    ):
        """Initialize therm material."""
        _ThermConditionBase.__init__(self, identifier)
        self.temperature = temperature
        self.film_coefficient = film_coefficient
        self.emissivity = emissivity
        self.radiant_temperature = radiant_temperature
        self.heat_flux = heat_flux
        self.relative_humidity = relative_humidity

    @property
    def temperature(self):
        """Get or set the temperature of the condition [C]."""
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        self._temperature = \
            float_in_range(value, mi=-273.15, input_name='condition temperature')

    @property
    def film_coefficient(self):
        """Get or set the film coefficient along the boundary [ W/m2-K]."""
        return self._film_coefficient

    @film_coefficient.setter
    def film_coefficient(self, value):
        self._film_coefficient = float_positive(value, 'film coefficient')

    @property
    def emissivity(self):
        """Get or set the hemispherical emissivity of the environment of the condition.
        """
        return self._emissivity

    @emissivity.setter
    def emissivity(self, ir_e):
        ir_e = float_in_range(ir_e, 0.0, 1.0, 'condition emissivity')
        self._emissivity = ir_e

    @property
    def radiant_temperature(self):
        """Get or set the radiant temperature along the boundary."""
        return self._radiant_temperature if self._radiant_temperature is not None \
            else self._temperature

    @radiant_temperature.setter
    def radiant_temperature(self, ir_t):
        if ir_t is not None:
            ir_t = float_in_range(ir_t, mi=-273.15,
                                  input_name='condition radiant temperature')
        self._radiant_temperature = ir_t

    @property
    def heat_flux(self):
        """Get or set the additional energy flux across the boundary [W/m2]."""
        return self._heat_flux

    @heat_flux.setter
    def heat_flux(self, value):
        self._heat_flux = float_positive(value, 'condition heat flux')

    @property
    def relative_humidity(self):
        """Get or set a number between zero and one for the relative humidity."""
        return self._relative_humidity

    @relative_humidity.setter
    def relative_humidity(self, value):
        self._relative_humidity = \
            float_in_range(value, 0.0, 1.0, 'condition relative humidity')

    @classmethod
    def from_therm_xml(cls, xml_element):
        """Create SteadyState from an XML element of a THERM BoundaryCondition.

        Args:
            xml_element: An XML element of a THERM BoundaryCondition.
        """
        # create the base material from the UUID, temperature, and film coefficient
        xml_uuid = xml_element.find('UUID')
        identifier = xml_uuid.text
        if len(identifier) == 31:
            identifier = uuid_from_therm_id(identifier)
        xml_comp = xml_element.find('Comprehensive')
        xml_conv = xml_comp.find('Convection')
        xml_t = xml_conv.find('Temperature')
        temperature = xml_t.text
        xml_fc = xml_conv.find('FilmCoefficient')
        film_coefficient = xml_fc.text
        cond = SteadyState(temperature, film_coefficient, identifier=identifier)
        # assign the other attributes if specified
        xml_rh = xml_comp.find('RelativeHumidity')
        if xml_rh is not None:
            cond.relative_humidity = xml_rh.text
        xml_flux = xml_comp.find('ConstantFlux')
        if xml_flux is not None:
            xml_fl = xml_flux.find('Flux')
            if xml_fl is not None:
                cond.heat_flux = xml_fl.text
        # assign the radiation properties if specified
        xml_rad = xml_comp.find('Radiation')
        if xml_rad is not None:
            xml_rm = xml_rad.find('BlackBodyRadiation')
            if xml_rm is None:
                xml_rm = xml_rad.find('AutomaticEnclosure')
            if xml_rm is not None:
                xml_mrt = xml_rm.find('Temperature')
                if xml_mrt is not None:
                    cond.radiant_temperature = xml_mrt.text
                xml_emiss = xml_rm.find('Emissivity')
                if xml_emiss is not None:
                    cond.emissivity = xml_emiss.text
        # assign the name and color if they are specified
        xml_name = xml_element.find('Name')
        if xml_name is not None:
            cond.display_name = xml_name.text
        xml_col = xml_element.find('Color')
        if xml_col is not None:
            cond.color = xml_col.text
        xml_protect = xml_element.find('Protected')
        if xml_protect is not None:
            cond.protected = True if xml_protect.text == 'true' else False
        xml_tag = xml_element.find('ProjectNameTag')
        if xml_tag is not None:
            cond.project_tag = xml_tag.text
        return cond

    @classmethod
    def from_therm_xml_str(cls, xml_str):
        """Create SteadyState from an XML string of a THERM BoundaryCondition.

        Args:
            xml_str: An XML text string of a THERM BoundaryCondition.
        """
        root = ET.fromstring(xml_str)
        return cls.from_therm_xml(root)

    @classmethod
    def from_dict(cls, data):
        """Create a SteadyState from a dictionary.

        Args:
            data: A python dictionary in the following format

        .. code-block:: python

            {
            "type": 'SteadyState',
            "identifier": 'f26f3597-e3ee-43fe-a0b3-ec673f993d86',
            "display_name": 'NFRC 100-2010 Exterior',
            "temperature": -18,
            "film_coefficient": 26,
            "emissivity": 1,
            "radiant_temperature": -18,
            "heat_flux": 0,
            "relative_humidity": 0.5
            }
        """
        assert data['type'] == 'SteadyState', \
            'Expected SteadyState. Got {}.'.format(data['type'])

        emiss = data['emissivity'] if 'emissivity' in data and \
            data['emissivity'] is not None else 1.0
        rad_temp = data['radiant_temperature'] if 'radiant_temperature' in data else None
        heat_flux = data['heat_flux'] if 'heat_flux' in data else 0
        rh = data['relative_humidity'] if 'relative_humidity' in data else 0.5

        new_cond = cls(
            data['temperature'], data['film_coefficient'],
            emiss, rad_temp, heat_flux, rh, data['identifier']
        )
        if 'display_name' in data and data['display_name'] is not None:
            new_cond.display_name = data['display_name']
        if 'color' in data and data['color'] is not None:
            new_cond.color = data['color']
        if 'protected' in data and data['protected'] is not None:
            new_cond.protected = data['protected']
        if 'project_tag' in data and data['project_tag']:
            new_cond._project_tag = data['project_tag']
        if 'user_data' in data and data['user_data'] is not None:
            new_cond.user_data = data['user_data']
        return new_cond

    def to_therm_xml(self, bcs_element=None):
        """Get an THERM XML element of the boundary condition.

        Args:
            bcs_element: An optional XML Element for the BoundaryConditions to
                which the generated objects will be added. If None, a new XML
                Element will be generated.

        .. code-block:: xml

            <BoundaryCondition>
                <UUID>1810f37a-de4d-4e2d-95d5-09fe01157c34</UUID>
                <Name>NFRC 100-2010 Exterior</Name>
                <ProjectNameTag></ProjectNameTag>
                <Protected>true</Protected>
                <Color>0x0080C0</Color>
                <IGUSurface>false</IGUSurface>
                <Comprehensive>
                    <RelativeHumidity>0.5</RelativeHumidity>
                    <Convection>
                        <Temperature>-18</Temperature>
                        <FilmCoefficient>26</FilmCoefficient>
                    </Convection>
                    <ConstantFlux>
                        <Flux>0</Flux>
                    </ConstantFlux>
                    <Radiation>
                        <BlackBodyRadiation>
                            <Temperature>-18</Temperature>
                            <Emissivity>1</Emissivity>
                            <ViewFactor>1</ViewFactor>
                        </BlackBodyRadiation>
                    </Radiation>
                </Comprehensive>
            </BoundaryCondition>
        """
        # create a new Materials element if one is not specified
        if bcs_element is not None:
            xml_cond = ET.SubElement(bcs_element, 'BoundaryCondition')
        else:
            xml_cond = ET.Element('BoundaryCondition')
        # add all of the required basic attributes
        xml_id = ET.SubElement(xml_cond, 'UUID')
        xml_id.text = self.identifier
        xml_name = ET.SubElement(xml_cond, 'Name')
        xml_name.text = self.display_name
        xml_tag = ET.SubElement(xml_cond, 'ProjectNameTag')
        if self.project_tag:
            xml_tag.text = self.project_tag
        xml_protect = ET.SubElement(xml_cond, 'Protected')
        xml_protect.text = 'true' if self.protected else 'false'
        xml_color = ET.SubElement(xml_cond, 'Color')
        xml_color.text = self.color.to_hex().replace('#', '0x')
        xml_igu = ET.SubElement(xml_cond, 'IGUSurface')
        xml_igu.text = 'false'
        if self.film_coefficient == 0 and self._radiant_temperature is None and \
                self.emissivity == 1 and self.heat_flux == 0:
            # keep a truly adiabatic condition simple; comprehensive XML carries
            # the independent radiation and flux terms even without convection.
            xml_simple = ET.SubElement(xml_cond, 'Simplified')
            xml_ct = ET.SubElement(xml_simple, 'Temperature')
            xml_ct.text = str(self.temperature)
            xml_fc = ET.SubElement(xml_simple, 'FilmCoefficient')
            xml_fc.text = '0'
            xml_rh = ET.SubElement(xml_simple, 'RelativeHumidity')
            xml_rh.text = str(self.relative_humidity)
        else:  # add all of the comprehensive attributes
            xml_comp = ET.SubElement(xml_cond, 'Comprehensive')
            xml_rh = ET.SubElement(xml_comp, 'RelativeHumidity')
            xml_rh.text = str(self.relative_humidity)
            xml_conv = ET.SubElement(xml_comp, 'Convection')
            xml_ct = ET.SubElement(xml_conv, 'Temperature')
            xml_ct.text = str(self.temperature)
            xml_fc = ET.SubElement(xml_conv, 'FilmCoefficient')
            xml_fc.text = str(self.film_coefficient)
            xml_heat = ET.SubElement(xml_comp, 'ConstantFlux')
            xml_flux = ET.SubElement(xml_heat, 'Flux')
            xml_flux.text = str(self.heat_flux)
            xml_rad = ET.SubElement(xml_comp, 'Radiation')
            xml_bb_rad = ET.SubElement(xml_rad, 'BlackBodyRadiation')
            xml_mrt = ET.SubElement(xml_bb_rad, 'Temperature')
            xml_mrt.text = str(self.radiant_temperature)
            xml_emiss = ET.SubElement(xml_bb_rad, 'Emissivity')
            xml_emiss.text = str(self.emissivity)
            xml_vf = ET.SubElement(xml_bb_rad, 'ViewFactor')
            # ponytail: scalar full view ignores self-view; add per-boundary factors
            # when enclosure geometry becomes an input.
            xml_vf.text = '1'
        return xml_cond

    def to_therm_xml_str(self):
        """Get an THERM XML string of the condition."""
        xml_root = self.to_therm_xml()
        try:  # try to indent the XML to make it read-able
            ET.indent(xml_root)
            return ET.tostring(xml_root, encoding='unicode')
        except AttributeError:  # we are in Python 2 and no indent is available
            return ET.tostring(xml_root)

    def to_dict(self):
        """SteadyState dictionary representation."""
        base = {
            'type': 'SteadyState',
            'identifier': self.identifier,
            'temperature': self.temperature,
            'film_coefficient': self.film_coefficient
        }
        if self.emissivity != 1:
            base['emissivity'] = self.emissivity
        if self._radiant_temperature is not None:
            base['radiant_temperature'] = self._radiant_temperature
        if self.heat_flux != 0:
            base['heat_flux'] = self.heat_flux
        if self._relative_humidity != 0.5:
            base['relative_humidity'] = self.relative_humidity
        if self._display_name is not None:
            base['display_name'] = self.display_name
        base['protected'] = self._protected
        base['color'] = self.color.to_hex()
        if self._project_tag is not None:
            base['project_tag'] = self.project_tag
        if self._user_data is not None:
            base['user_data'] = self.user_data
        return base

    @staticmethod
    def extract_all_from_xml_file(xml_file):
        """Extract all Condition objects from a THERM XML file.

        Args:
            xml_file: A path to an XML file containing objects Condition objects.

        Returns:
            A list of all Comprehensive Condition objects in the file.
        """
        # read the file and get the root
        tree = ET.parse(xml_file)
        root = tree.getroot()
        # extract all of the PureGas objects
        conditions = []
        for con_obj in root:
            if con_obj.tag == 'BoundaryCondition' and \
                    con_obj.find('Comprehensive') is not None:
                SteadyState.from_therm_xml(con_obj)
                try:
                    conditions.append(SteadyState.from_therm_xml(con_obj))
                except Exception:  # not a valid conditions
                    pass
        return conditions

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.identifier, self.temperature, self.film_coefficient,
                self.emissivity, self.radiant_temperature, self.heat_flux,
                self.relative_humidity)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, SteadyState) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        new_cond = self.__class__(
            self.temperature, self.film_coefficient,
            self._emissivity, self._radiant_temperature, self._heat_flux,
            self._relative_humidity, self.identifier
        )
        new_cond._display_name = self._display_name
        new_cond._color = self._color
        new_cond._protected = self._protected
        new_cond._project_tag = self._project_tag
        new_cond._user_data = None if self._user_data is None \
            else self._user_data.copy()
        return new_cond

    def __repr__(self):
        return 'Comprehensive THERM Condition: {}'.format(self.display_name)
