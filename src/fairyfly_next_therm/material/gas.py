# coding=utf-8
"""Gas materials."""
from __future__ import division
import xml.etree.ElementTree as ET

from fairyfly._lockable import lockable
from fairyfly.typing import float_positive, float_in_range, tuple_with_length, \
    uuid_from_therm_id

from ._base import _ResourceObjectBase


@lockable
class PureGas(_ResourceObjectBase):
    """Custom gas gap layer.

    This object allows you to specify specific values for conductivity,
    viscosity and specific heat through the following formula:

    property = A + (B * T) + (C * T ** 2)

    where:

    * A, B, and C = regression coefficients for the gas
    * T = temperature [K]

    Note that setting properties B and C to 0 will mean the property will be
    equal to the A coefficient.

    Args:
        conductivity_coeff_a: First conductivity coefficient.
            Or conductivity in [W/m-K] if b and c coefficients are 0.
        viscosity_coeff_a: First viscosity coefficient.
            Or viscosity in [kg/m-s] if b and c coefficients are 0.
        specific_heat_coeff_a: First specific heat coefficient.
            Or specific heat in [J/kg-K] if b and c coefficients are 0.
        conductivity_coeff_b: Second conductivity coefficient. Default = 0.
        viscosity_coeff_b: Second viscosity coefficient. Default = 0.
        specific_heat_coeff_b: Second specific heat coefficient. Default = 0.
        conductivity_coeff_c: Third conductivity coefficient. Default = 0.
        viscosity_coeff_c: Third viscosity coefficient. Default = 0.
        specific_heat_coeff_c: Third specific heat coefficient. Default = 0.
        specific_heat_ratio: A number for the the ratio of the specific heat at
            constant pressure, to the specific heat at constant volume.
            Default is 1.0 for Air.
        molecular_weight: Number between 20 and 200 for the mass of 1 mol of
            the substance in grams. Default is 20.0.
        identifier: Text string for a unique object ID. Must be a UUID in the
            format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx. If None, a UUID will
            automatically be generated. (Default: None).

    Properties:
        * identifier
        * display_name
        * conductivity_coeff_a
        * viscosity_coeff_a
        * specific_heat_coeff_a
        * conductivity_coeff_b
        * viscosity_coeff_b
        * specific_heat_coeff_b
        * conductivity_coeff_c
        * viscosity_coeff_c
        * specific_heat_coeff_c
        * specific_heat_ratio
        * molecular_weight
        * protected
        * user_data

    Usage:

    .. code-block:: python

        co2_mat = PureGas(0.0146, 0.000014, 827.73)
        co2_mat.display_name = 'CO2'
        co2_gap.specific_heat_ratio = 1.4
        co2_gap.molecular_weight = 44
        print(co2_gap)
    """
    __slots__ = ('_conductivity_coeff_a', '_viscosity_coeff_a', '_specific_heat_coeff_a',
                 '_conductivity_coeff_b', '_viscosity_coeff_b', '_specific_heat_coeff_b',
                 '_conductivity_coeff_c', '_viscosity_coeff_c', '_specific_heat_coeff_c',
                 '_specific_heat_ratio', '_molecular_weight')

    def __init__(
            self, conductivity_coeff_a, viscosity_coeff_a, specific_heat_coeff_a,
            conductivity_coeff_b=0, viscosity_coeff_b=0, specific_heat_coeff_b=0,
            conductivity_coeff_c=0, viscosity_coeff_c=0, specific_heat_coeff_c=0,
            specific_heat_ratio=1.0, molecular_weight=20.0, identifier=None):
        """Initialize custom gas energy material."""
        _ResourceObjectBase.__init__(self, identifier)
        self.conductivity_coeff_a = conductivity_coeff_a
        self.viscosity_coeff_a = viscosity_coeff_a
        self.specific_heat_coeff_a = specific_heat_coeff_a
        self.conductivity_coeff_b = conductivity_coeff_b
        self.viscosity_coeff_b = viscosity_coeff_b
        self.specific_heat_coeff_b = specific_heat_coeff_b
        self.conductivity_coeff_c = conductivity_coeff_c
        self.viscosity_coeff_c = viscosity_coeff_c
        self.specific_heat_coeff_c = specific_heat_coeff_c
        self.specific_heat_ratio = specific_heat_ratio
        self.molecular_weight = molecular_weight

    @property
    def conductivity_coeff_a(self):
        """Get or set the first conductivity coefficient."""
        return self._conductivity_coeff_a

    @conductivity_coeff_a.setter
    def conductivity_coeff_a(self, coeff):
        self._conductivity_coeff_a = float(coeff)

    @property
    def viscosity_coeff_a(self):
        """Get or set the first viscosity coefficient."""
        return self._viscosity_coeff_a

    @viscosity_coeff_a.setter
    def viscosity_coeff_a(self, coeff):
        self._viscosity_coeff_a = float_positive(coeff)

    @property
    def specific_heat_coeff_a(self):
        """Get or set the first specific heat coefficient."""
        return self._specific_heat_coeff_a

    @specific_heat_coeff_a.setter
    def specific_heat_coeff_a(self, coeff):
        self._specific_heat_coeff_a = float_positive(coeff)

    @property
    def conductivity_coeff_b(self):
        """Get or set the second conductivity coefficient."""
        return self._conductivity_coeff_b

    @conductivity_coeff_b.setter
    def conductivity_coeff_b(self, coeff):
        self._conductivity_coeff_b = float(coeff)

    @property
    def viscosity_coeff_b(self):
        """Get or set the second viscosity coefficient."""
        return self._viscosity_coeff_b

    @viscosity_coeff_b.setter
    def viscosity_coeff_b(self, coeff):
        self._viscosity_coeff_b = float(coeff)

    @property
    def specific_heat_coeff_b(self):
        """Get or set the second specific heat coefficient."""
        return self._specific_heat_coeff_b

    @specific_heat_coeff_b.setter
    def specific_heat_coeff_b(self, coeff):
        self._specific_heat_coeff_b = float(coeff)

    @property
    def conductivity_coeff_c(self):
        """Get or set the third conductivity coefficient."""
        return self._conductivity_coeff_c

    @conductivity_coeff_c.setter
    def conductivity_coeff_c(self, coeff):
        self._conductivity_coeff_c = float(coeff)

    @property
    def viscosity_coeff_c(self):
        """Get or set the third viscosity coefficient."""
        return self._viscosity_coeff_c

    @viscosity_coeff_c.setter
    def viscosity_coeff_c(self, coeff):
        self._viscosity_coeff_c = float(coeff)

    @property
    def specific_heat_coeff_c(self):
        """Get or set the third specific heat coefficient."""
        return self._specific_heat_coeff_c

    @specific_heat_coeff_c.setter
    def specific_heat_coeff_c(self, coeff):
        self._specific_heat_coeff_c = float(coeff)

    @property
    def specific_heat_ratio(self):
        """Get or set the specific heat ratio."""
        return self._specific_heat_ratio

    @specific_heat_ratio.setter
    def specific_heat_ratio(self, number):
        number = float(number)
        assert 1 <= number, 'Input specific_heat_ratio ({}) must be > 1.'.format(number)
        self._specific_heat_ratio = number

    @property
    def molecular_weight(self):
        """Get or set the molecular weight."""
        return self._molecular_weight

    @molecular_weight.setter
    def molecular_weight(self, number):
        self._molecular_weight = float_in_range(
            number, 2.0, 300.0, 'gas material molecular weight')

    @property
    def conductivity(self):
        """Conductivity of the gas in the absence of convection at 0C [W/m-K]."""
        return self.conductivity_at_temperature(273.15)

    @property
    def viscosity(self):
        """Viscosity of the gas at 0C [kg/m-s]."""
        return self.viscosity_at_temperature(273.15)

    @property
    def specific_heat(self):
        """Specific heat of the gas at 0C [J/kg-K]."""
        return self.specific_heat_at_temperature(273.15)

    @property
    def density(self):
        """Density of the gas at 0C and sea-level pressure [J/kg-K]."""
        return self.density_at_temperature(273.15)

    @property
    def prandtl(self):
        """Prandtl number of the gas at 0C."""
        return self.prandtl_at_temperature(273.15)

    def conductivity_at_temperature(self, t_kelvin):
        """Get the conductivity of the gas [W/m-K] at a given Kelvin temperature."""
        return self.conductivity_coeff_a + self.conductivity_coeff_b * t_kelvin + \
            self.conductivity_coeff_c * t_kelvin ** 2

    def viscosity_at_temperature(self, t_kelvin):
        """Get the viscosity of the gas [kg/m-s] at a given Kelvin temperature."""
        return self.viscosity_coeff_a + self.viscosity_coeff_b * t_kelvin + \
            self.viscosity_coeff_c * t_kelvin ** 2

    def specific_heat_at_temperature(self, t_kelvin):
        """Get the specific heat of the gas [J/kg-K] at a given Kelvin temperature."""
        return self.specific_heat_coeff_a + self.specific_heat_coeff_b * t_kelvin + \
            self.specific_heat_coeff_c * t_kelvin ** 2

    def density_at_temperature(self, t_kelvin, pressure=101325):
        """Get the density of the gas [kg/m3] at a given temperature and pressure.

        This method uses the ideal gas law to estimate the density.

        Args:
            t_kelvin: The average temperature of the gas cavity in Kelvin.
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        return (pressure * self.molecular_weight * 0.001) / (8.314 * t_kelvin)

    def prandtl_at_temperature(self, t_kelvin):
        """Get the Prandtl number of the gas at a given Kelvin temperature."""
        return self.viscosity_at_temperature(t_kelvin) * \
            self.specific_heat_at_temperature(t_kelvin) / \
            self.conductivity_at_temperature(t_kelvin)

    @classmethod
    def from_therm_xml(cls, xml_element):
        """Create PureGas from an XML element of a THERM PureGas material.

        Args:
            xml_element: An XML element of a THERM PureGas material.
        """
        # get the identifier, molecular weight and specific heat ratio
        xml_uuid = xml_element.find('UUID')
        identifier = xml_uuid.text
        if len(identifier) == 31:
            identifier = uuid_from_therm_id(identifier)
        xml_prop = xml_element.find('Properties')
        xml_mw = xml_prop.find('MolecularWeight')
        molecular_weight = xml_mw.text
        xml_shr = xml_prop.find('SpecificHeatRatio')
        specific_heat_ratio = xml_shr.text
        # extract the conductivity curve
        xml_cond = xml_prop.find('Conductivity')
        xml_c_a = xml_cond.find('A')
        conductivity_coeff_a = xml_c_a.text
        xml_c_b = xml_cond.find('B')
        conductivity_coeff_b = xml_c_b.text
        xml_c_c = xml_cond.find('C')
        conductivity_coeff_c = xml_c_c.text
        # extract the viscosity curve
        xml_vis = xml_prop.find('Viscosity')
        xml_v_a = xml_vis.find('A')
        viscosity_coeff_a = xml_v_a.text
        xml_v_b = xml_vis.find('B')
        viscosity_coeff_b = xml_v_b.text
        xml_v_c = xml_vis.find('C')
        viscosity_coeff_c = xml_v_c.text
        # extract the specific heat curve
        xml_sh = xml_prop.find('SpecificHeat')
        xml_sh_a = xml_sh.find('A')
        specific_heat_coeff_a = xml_sh_a.text
        xml_sh_b = xml_sh.find('B')
        specific_heat_coeff_b = xml_sh_b.text
        xml_sh_c = xml_sh.find('C')
        specific_heat_coeff_c = xml_sh_c.text
        # create the PureGas material
        mat = PureGas(
            conductivity_coeff_a, viscosity_coeff_a, specific_heat_coeff_a,
            conductivity_coeff_b, viscosity_coeff_b, specific_heat_coeff_b,
            conductivity_coeff_c, viscosity_coeff_c, specific_heat_coeff_c,
            specific_heat_ratio, molecular_weight, identifier=identifier)
        # assign the name if it is specified
        xml_name = xml_element.find('Name')
        if xml_name is not None:
            mat.display_name = xml_name.text
        xml_protect = xml_element.find('Protected')
        if xml_protect is not None:
            mat.protected = True if xml_protect.text == 'true' else False
        return mat

    @classmethod
    def from_therm_xml_str(cls, xml_str):
        """Create a PureGas from an XML text string of a THERM PureGas.

        Args:
            xml_str: An XML text string of a THERM PureGas.
        """
        root = ET.fromstring(xml_str)
        return cls.from_therm_xml(root)

    @classmethod
    def from_dict(cls, data):
        """Create a PureGas from a dictionary.

        Args:
            data: A python dictionary in the following format

        .. code-block:: python

            {
            "type": 'PureGas',
            "identifier": '7b4a5a47-ebec-4d95-b028-a78485130c34',
            "display_name": 'CO2'
            "conductivity_coeff_a": 0.0146,
            "viscosity_coeff_a": 0.000014,
            "specific_heat_coeff_a": 827.73,
            "specific_heat_ratio": 1.4
            "molecular_weight": 44
            }
        """
        assert data['type'] == 'PureGas', \
            'Expected PureGas. Got {}.'.format(data['type'])
        con_b = 0 if 'conductivity_coeff_b' not in data else data['conductivity_coeff_b']
        vis_b = 0 if 'viscosity_coeff_b' not in data else data['viscosity_coeff_b']
        sph_b = 0 if 'specific_heat_coeff_b' not in data \
            else data['specific_heat_coeff_b']
        con_c = 0 if 'conductivity_coeff_c' not in data else data['conductivity_coeff_c']
        vis_c = 0 if 'viscosity_coeff_c' not in data else data['viscosity_coeff_c']
        sph_c = 0 if 'specific_heat_coeff_c' not in data \
            else data['specific_heat_coeff_c']
        sphr = 1.0 if 'specific_heat_ratio' not in data else data['specific_heat_ratio']
        mw = 20.0 if 'molecular_weight' not in data else data['molecular_weight']
        new_obj = cls(
            data['conductivity_coeff_a'], data['viscosity_coeff_a'],
            data['specific_heat_coeff_a'],
            con_b, vis_b, sph_b, con_c, vis_c, sph_c, sphr, mw,
            identifier=data['identifier'])
        if 'display_name' in data and data['display_name'] is not None:
            new_obj.display_name = data['display_name']
        if 'protected' in data and data['protected'] is not None:
            new_obj.protected = data['protected']
        if 'user_data' in data and data['user_data'] is not None:
            new_obj.user_data = data['user_data']
        return new_obj

    def to_therm_xml(self, gases_element=None):
        """Get an THERM XML element of the gas.

        Args:
            gases_element: An optional XML Element for the Gases to which the
                generated objects will be added. If None, a new XML Element
                will be generated.

        .. code-block:: xml

            <PureGas>
                <UUID>8d33196f-f052-46e6-8353-bccb9a779f9c</UUID>
                <Name>Air</Name>
                <Protected>true</Protected>
                <Properties>
                    <MolecularWeight>28.97</MolecularWeight>
                    <SpecificHeatRatio>1.4</SpecificHeatRatio>
                    <Conductivity>
                        <A>0.002873</A>
                        <B>7.76e-05</B>
                        <C>0</C>
                    </Conductivity>
                    <Viscosity>
                        <A>3.723e-06</A>
                        <B>4.94e-08</B>
                        <C>0</C>
                    </Viscosity>
                    <SpecificHeat>
                        <A>1002.737</A>
                        <B>0.012324</B>
                        <C>0</C>
                    </SpecificHeat>
                </Properties>
            </PureGas>
        """
        # create a new Materials element if one is not specified
        if gases_element is not None:
            xml_mat = ET.SubElement(gases_element, 'PureGas')
        else:
            xml_mat = ET.Element('PureGas')
        # add all of the required basic attributes
        xml_id = ET.SubElement(xml_mat, 'UUID')
        xml_id.text = self.identifier
        xml_name = ET.SubElement(xml_mat, 'Name')
        xml_name.text = self.display_name
        xml_protect = ET.SubElement(xml_mat, 'Protected')
        xml_protect.text = 'true' if self.protected else 'false'
        xml_prop = ET.SubElement(xml_mat, 'Properties')
        # molecular weight and specific heat ratio
        xml_mw = ET.SubElement(xml_prop, 'MolecularWeight')
        xml_mw.text = str(self.molecular_weight)
        xml_shr = ET.SubElement(xml_prop, 'SpecificHeatRatio')
        xml_shr.text = str(self.specific_heat_ratio)
        # add the conductivity curve
        xml_cond = ET.SubElement(xml_prop, 'Conductivity')
        xml_cond_a = ET.SubElement(xml_cond, 'A')
        xml_cond_a.text = str(self.conductivity_coeff_a)
        xml_cond_b = ET.SubElement(xml_cond, 'B')
        xml_cond_b.text = str(self.conductivity_coeff_b)
        xml_cond_c = ET.SubElement(xml_cond, 'C')
        xml_cond_c.text = str(self.conductivity_coeff_c)
        # add the viscosity curve
        xml_vis = ET.SubElement(xml_prop, 'Viscosity')
        xml_vis_a = ET.SubElement(xml_vis, 'A')
        xml_vis_a.text = str(self.viscosity_coeff_a)
        xml_vis_b = ET.SubElement(xml_vis, 'B')
        xml_vis_b.text = str(self.viscosity_coeff_b)
        xml_vis_c = ET.SubElement(xml_vis, 'C')
        xml_vis_c.text = str(self.viscosity_coeff_c)
        # add the specific heat curve
        xml_sh = ET.SubElement(xml_prop, 'SpecificHeat')
        xml_sh_a = ET.SubElement(xml_sh, 'A')
        xml_sh_a.text = str(self.specific_heat_coeff_a)
        xml_sh_b = ET.SubElement(xml_sh, 'B')
        xml_sh_b.text = str(self.specific_heat_coeff_b)
        xml_sh_c = ET.SubElement(xml_sh, 'C')
        xml_sh_c.text = str(self.specific_heat_coeff_c)
        return xml_mat

    def to_therm_xml_str(self):
        """Get an THERM XML string of the gas."""
        xml_root = self.to_therm_xml()
        try:  # try to indent the XML to make it read-able
            ET.indent(xml_root)
            return ET.tostring(xml_root, encoding='unicode')
        except AttributeError:  # we are in Python 2 and no indent is available
            return ET.tostring(xml_root)

    def to_dict(self):
        """PureGas dictionary representation."""
        base = {
            'type': 'PureGas',
            'identifier': self.identifier,
            'conductivity_coeff_a': self.conductivity_coeff_a,
            'viscosity_coeff_a': self.viscosity_coeff_a,
            'specific_heat_coeff_a': self.specific_heat_coeff_a,
            'conductivity_coeff_b': self.conductivity_coeff_b,
            'viscosity_coeff_b': self.viscosity_coeff_b,
            'specific_heat_coeff_b': self.specific_heat_coeff_b,
            'conductivity_coeff_c': self.conductivity_coeff_c,
            'viscosity_coeff_c': self.viscosity_coeff_c,
            'specific_heat_coeff_c': self.specific_heat_coeff_c,
            'specific_heat_ratio': self.specific_heat_ratio,
            'molecular_weight': self.molecular_weight
        }
        if self._display_name is not None:
            base['display_name'] = self.display_name
        base['protected'] = self._protected
        if self._user_data is not None:
            base['user_data'] = self.user_data
        return base

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.identifier, self.conductivity_coeff_a,
                self.viscosity_coeff_a, self.specific_heat_coeff_a,
                self.conductivity_coeff_b, self.viscosity_coeff_b,
                self.specific_heat_coeff_b, self.conductivity_coeff_c,
                self.viscosity_coeff_c, self.specific_heat_coeff_c,
                self.specific_heat_ratio, self.molecular_weight)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, PureGas) and \
            self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'THERM Pure Gas: {}'.format(self.display_name)

    def __copy__(self):
        new_obj = PureGas(
            self.conductivity_coeff_a, self.viscosity_coeff_a, self.specific_heat_coeff_a,
            self.conductivity_coeff_b, self.viscosity_coeff_b, self.specific_heat_coeff_b,
            self.conductivity_coeff_c, self.viscosity_coeff_c, self.specific_heat_coeff_c,
            self.specific_heat_ratio, self.molecular_weight, identifier=self.identifier)
        new_obj._display_name = self._display_name
        new_obj._protected = self._protected
        new_obj._user_data = None if self._user_data is None else self._user_data.copy()
        return new_obj


@lockable
class Gas(_ResourceObjectBase):
    """Gas gap material defined by a mixture of gases.

    Args:
        pure_gases: A list of PureGas objects describing the types of gas in the gap.
        gas_fractions: A list of fractional numbers describing the volumetric
            fractions of gas types in the mixture.  This list must align with
            the pure_gases input list and must sum to 1.
        identifier: Text string for a unique object ID. Must be a UUID in the
            format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx. If None, a UUID will
            automatically be generated. (Default: None).

    Properties:
        * identifier
        * display_name
        * pure_gases
        * gas_fractions
        * gas_count
        * protected
        * user_data
    """
    __slots__ = ('_gas_count', '_pure_gases', '_gas_fractions')

    def __init__(self, pure_gases, gas_fractions, identifier=None):
        """Initialize gas mixture material."""
        _ResourceObjectBase.__init__(self, identifier)
        try:  # check the number of gases
            self._gas_count = len(pure_gases)
        except (TypeError, ValueError):
            raise TypeError(
                'Expected list for pure_gases. Got {}.'.format(type(pure_gases)))
        assert 1 <= self._gas_count, 'Number of gases in gas mixture must be ' \
            'greater than 1. Got {}.'.format(self._gas_count)
        self.pure_gases = pure_gases
        self.gas_fractions = gas_fractions

    @property
    def pure_gases(self):
        """Get or set a tuple of text describing the gases in the gas gap layer."""
        return self._pure_gases

    @pure_gases.setter
    def pure_gases(self, value):
        try:
            if not isinstance(value, tuple):
                value = tuple(value)
        except TypeError:
            raise TypeError('Expected list or tuple for pure_gases. '
                            'Got {}'.format(type(value)))
        for g in value:
            assert isinstance(g, PureGas), 'Expected PureGas' \
                ' material for Gas. Got {}.'.format(type(g))
        assert len(value) > 0, 'Gas must possess at least one pure gas.'
        self._pure_gases = value

    @property
    def gas_fractions(self):
        """Get or set a tuple of numbers the fractions of gases in the gas gap layer."""
        return self._gas_fractions

    @gas_fractions.setter
    def gas_fractions(self, g_fracs):
        self._gas_fractions = tuple_with_length(
            g_fracs, self._gas_count, float, 'gas mixture gas_fractions')
        assert sum(self._gas_fractions) == 1, 'Gas fractions must sum to 1. ' \
            'Got {}.'.format(sum(self._gas_fractions))

    @property
    def molecular_weight(self):
        """Get the gas molecular weight."""
        return sum(tuple(gas.molecular_weight * frac for gas, frac
                         in zip(self._pure_gases, self._gas_fractions)))

    @property
    def gas_count(self):
        """An integer indicating the number of gases in the mixture."""
        return self._gas_count

    @property
    def conductivity(self):
        """Conductivity of the gas in the absence of convection at 0C [W/m-K]."""
        return self.conductivity_at_temperature(273.15)

    @property
    def viscosity(self):
        """Viscosity of the gas at 0C [kg/m-s]."""
        return self.viscosity_at_temperature(273.15)

    @property
    def specific_heat(self):
        """Specific heat of the gas at 0C [J/kg-K]."""
        return self.specific_heat_at_temperature(273.15)

    @property
    def density(self):
        """Density of the gas at 0C and sea-level pressure [J/kg-K]."""
        return self.density_at_temperature(273.15)

    @property
    def prandtl(self):
        """Prandtl number of the gas at 0C."""
        return self.prandtl_at_temperature(273.15)

    def conductivity_at_temperature(self, t_kelvin):
        """Get the conductivity of the gas [W/m-K] at a given Kelvin temperature."""
        return self._weighted_avg_coeff_property('conductivity_coeff', t_kelvin)

    def viscosity_at_temperature(self, t_kelvin):
        """Get the viscosity of the gas [kg/m-s] at a given Kelvin temperature."""
        return self._weighted_avg_coeff_property('viscosity_coeff', t_kelvin)

    def specific_heat_at_temperature(self, t_kelvin):
        """Get the specific heat of the gas [J/kg-K] at a given Kelvin temperature."""
        return self._weighted_avg_coeff_property('specific_heat_coeff', t_kelvin)

    def density_at_temperature(self, t_kelvin, pressure=101325):
        """Get the density of the gas [kg/m3] at a given temperature and pressure.

        This method uses the ideal gas law to estimate the density.

        Args:
            t_kelvin: The average temperature of the gas cavity in Kelvin.
            pressure: The average pressure of the gas cavity in Pa.
                Default is 101325 Pa for standard pressure at sea level.
        """
        return (pressure * self.molecular_weight * 0.001) / (8.314 * t_kelvin)

    def prandtl_at_temperature(self, t_kelvin):
        """Get the Prandtl number of the gas at a given Kelvin temperature."""
        return self.viscosity_at_temperature(t_kelvin) * \
            self.specific_heat_at_temperature(t_kelvin) / \
            self.conductivity_at_temperature(t_kelvin)

    @classmethod
    def from_therm_xml(cls, xml_element, pure_gases):
        """Create Gas from an XML element of a THERM Gas material.

        Args:
            xml_element: An XML element of a THERM Gas material.
            pure_gases: A dictionary with pure gas names as keys and PureGas
                object instances as values. These will be used to reassign
                the pure gases that make up this gas.
        """
        # get the identifier, gases and initialize the object
        xml_uuid = xml_element.find('UUID')
        identifier = xml_uuid.text
        if len(identifier) == 31:
            identifier = uuid_from_therm_id(identifier)
        xml_comps = xml_element.find('Components')
        pure_gas_objs, gas_fractions = [], []
        for xml_comp in xml_comps:
            xml_gas_name = xml_comp.find('PureGas')
            try:
                pure_gas_objs.append(pure_gases[xml_gas_name.text])
            except KeyError as e:
                raise ValueError('Failed to find {} in pure gases.'.format(e))
            xml_gas_fract = xml_comp.find('Fraction')
            gas_fractions.append(xml_gas_fract.text)
        mat = Gas(pure_gas_objs, gas_fractions, identifier=identifier)
        # assign the name if it is specified
        xml_name = xml_element.find('Name')
        if xml_name is not None:
            mat.display_name = xml_name.text
        xml_protect = xml_element.find('Protected')
        if xml_protect is not None:
            mat.protected = True if xml_protect.text == 'true' else False
        return mat

    @classmethod
    def from_therm_xml_str(cls, xml_str, pure_gases):
        """Create a Gas from an XML text string of a THERM Gas.

        Args:
            xml_str: An XML text string of a THERM Gas.
            pure_gases: A dictionary with pure gas names as keys and PureGas
                object instances as values. These will be used to reassign
                the pure gases that make up this gas gap.
        """
        root = ET.fromstring(xml_str)
        return cls.from_therm_xml(root, pure_gases)

    @classmethod
    def from_dict(cls, data):
        """Create a Gas from a dictionary.

        Args:
            data: A python dictionary in the following format

        .. code-block:: python

            {
            'type': 'Gas',
            'identifier': 'e34f4b07-a012-4142-ae29-d7967c921c71',
            'display_name': 'Argon Mixture',
            'pure_gases': [{}, {}],  # list of PureGas objects
            'gas_fractions': [0.95, 0.05]
            }
        """
        assert data['type'] == 'Gas', 'Expected Gas. Got {}.'.format(data['type'])
        pure_gases = [PureGas.from_dict(pg) for pg in data['pure_gases']]
        new_obj = cls(pure_gases, data['gas_fractions'], data['identifier'])
        cls._assign_optional_from_dict(new_obj, data)
        return new_obj

    @classmethod
    def from_dict_abridged(cls, data, pure_gases):
        """Create a Gas from an abridged dictionary.

        Args:
            data: An GasAbridged dictionary.
            pure_gases: A dictionary with pure gas identifiers as keys and PureGas
                object instances as values. These will be used to reassign
                the pure gases that make up this gas gap.

        .. code-block:: python

            {
            'type': 'GasAbridged',
            'identifier': 'e34f4b07-a012-4142-ae29-d7967c921c71',
            'display_name': 'Argon Mixture',
            'pure_gases': [
                'ca280a4b-aba9-416f-9443-484285d52227',
                'ba65b928-f766-4044-bc17-e53c42040bde'
            ],
            'gas_fractions': [0.95, 0.05]
            }
        """
        assert data['type'] == 'GasAbridged', \
            'Expected GasAbridged. Got {}.'.format(data['type'])
        try:
            pure_gas_objs = [pure_gases[mat_id] for mat_id in data['pure_gases']]
        except KeyError as e:
            raise ValueError('Failed to find {} in pure gases.'.format(e))
        new_obj = cls(pure_gas_objs, data['gas_fractions'], data['identifier'])
        cls._assign_optional_from_dict(new_obj, data)
        return new_obj

    @staticmethod
    def _assign_optional_from_dict(new_obj, data):
        """Assign optional attributes when serializing from dict."""
        if 'display_name' in data and data['display_name'] is not None:
            new_obj.display_name = data['display_name']
        if 'protected' in data and data['protected'] is not None:
            new_obj.protected = data['protected']
        if 'user_data' in data and data['user_data'] is not None:
            new_obj.user_data = data['user_data']

    def to_therm_xml(self, gases_element=None):
        """Get an THERM XML element of the gas.

        Note that this method only outputs a single element for the gas and,
        to write the full gas into an XML, the gas's pure gases
        must also be written.

        Args:
            gases_element: An optional XML Element for the Gases to which the
                generated objects will be added. If None, a new XML Element
                will be generated.

        .. code-block:: xml

            <Gas>
                <UUID>6c2409e9-5296-46c1-be11-9029b59a549b</UUID>
                <Name>Air</Name>
                <Protected>true</Protected>
                <Components>
                    <Component>
                        <Fraction>1</Fraction>
                        <PureGas>Air</PureGas>
                    </Component>
                </Components>
            </Gas>
        """
        # create a new Materials element if one is not specified
        if gases_element is not None:
            xml_mat = ET.SubElement(gases_element, 'Gas')
        else:
            xml_mat = ET.Element('Gas')
        # add all of the required basic attributes
        xml_id = ET.SubElement(xml_mat, 'UUID')
        xml_id.text = self.identifier
        xml_name = ET.SubElement(xml_mat, 'Name')
        xml_name.text = self.display_name
        xml_protect = ET.SubElement(xml_mat, 'Protected')
        xml_protect.text = 'true' if self.protected else 'false'
        # add the gas components
        xml_comps = ET.SubElement(xml_mat, 'Components')
        for pure_gas, gas_fract in zip(self.pure_gases, self.gas_fractions):
            xml_comp = ET.SubElement(xml_comps, 'Component')
            xml_fact = ET.SubElement(xml_comp, 'Fraction')
            xml_fact.text = str(gas_fract)
            xml_gas = ET.SubElement(xml_comp, 'PureGas')
            xml_gas.text = pure_gas.display_name
        return xml_mat

    def to_therm_xml_str(self):
        """Get an THERM XML string of the gas."""
        xml_root = self.to_therm_xml()
        try:  # try to indent the XML to make it read-able
            ET.indent(xml_root)
            return ET.tostring(xml_root, encoding='unicode')
        except AttributeError:  # we are in Python 2 and no indent is available
            return ET.tostring(xml_root)

    def to_dict(self, abridged=False):
        """Gas dictionary representation."""
        base = {'type': 'Gas'} if not abridged else {'type': 'GasAbridged'}
        base['identifier'] = self.identifier
        base['pure_gases'] = \
            [m.identifier for m in self.pure_gases] if abridged else \
            [m.to_dict() for m in self.pure_gases]
        base['gas_fractions'] = self.gas_fractions
        if self._display_name is not None:
            base['display_name'] = self.display_name
        base['protected'] = self._protected
        if self._user_data is not None:
            base['user_data'] = self.user_data
        return base

    def lock(self):
        """The lock() method will also lock the pure gases."""
        self._locked = True
        for gas in self.pure_gases:
            gas.lock()

    def unlock(self):
        """The unlock() method will also unlock the pure gases."""
        self._locked = False
        for gas in self.pure_gases:
            gas.unlock()

    @staticmethod
    def extract_all_from_xml_file(xml_file):
        """Extract all Gas objects from a THERM XML file.

        Args:
            xml_file: A path to an XML file containing objects Gas objects and
                corresponding PureGas components.

        Returns:
            A tuple with two elements

            -   gases: A list of all Gas objects in the XML file as fairyfly_next_therm
                Gas objects.

            -   pure_gases: A list of all PureGas objects in the XML file as
                fairyfly_next_therm PureGas objects.
        """
        # read the file and get the root
        tree = ET.parse(xml_file)
        root = tree.getroot()
        # extract all of the PureGas objects
        pure_dict = {}
        for gas_obj in root:
            if gas_obj.tag == 'PureGas':
                try:
                    xml_name = gas_obj.find('Name')
                    pure_dict[xml_name.text] = PureGas.from_therm_xml(gas_obj)
                except Exception:  # not a valid pure gas material
                    pass
        # extract all of the gas objects
        gases = []
        for gas_obj in root:
            if gas_obj.tag == 'Gas':
                try:
                    gases.append(Gas.from_therm_xml(gas_obj, pure_dict))
                except Exception:  # not a valid gas material
                    pass
        return gases, list(pure_dict.values())

    def _weighted_avg_coeff_property(self, attr, t_kelvin):
        """Get a weighted average property given a dictionary of coefficients."""
        property = []
        for gas in self._pure_gases:
            property.append(
                getattr(gas, attr + '_a') +
                getattr(gas, attr + '_b') * t_kelvin +
                getattr(gas, attr + '_c') * t_kelvin ** 2)
        return sum(tuple(pr * frac for pr, frac in zip(property, self._gas_fractions)))

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.identifier, self.gas_fractions) + \
            tuple(hash(g) for g in self.pure_gases)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, Gas) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'THERM Gas: {}'.format(self.display_name)

    def __copy__(self):
        new_obj = Gas(
            [g.duplicate() for g in self.pure_gases],
            self.gas_fractions, self.identifier)
        new_obj._display_name = self._display_name
        new_obj._protected = self._protected
        new_obj._user_data = None if self._user_data is None else self._user_data.copy()
        return new_obj
