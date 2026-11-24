# coding=utf-8
"""Hygrothermal THERM material."""
from __future__ import division
import math
import xml.etree.ElementTree as ET

from fairyfly._lockable import lockable
from fairyfly.typing import float_in_range, float_positive, \
    uuid_from_therm_id

from ._base import _ThermMaterialBase


@lockable
class HygrothermalMaterial(_ThermMaterialBase):
    """Conductive material with moisture storage and transport properties.

    This object mirrors the full THERM ``Material/Solid/HygroThermal`` record,
    adding the moisture-dependent tables that a dry SolidMaterial does not
    carry. Tables are given as lists of (x, y) pairs where the meaning of
    each pair is dictated by the THERM schema.

    Args:
        conductivity: Number for the thermal conductivity of the dry material
            [W/m-K].
        density: Optional number for the bulk density [kg/m3]. (Default: None).
        porosity: Optional number between zero and one for the porosity.
            (Default: None).
        specific_heat: Optional number for the specific heat capacity of the
            dry material [J/kg-K]. (Default: None).
        vapor_diffusion_resistance: Optional number for the water vapor
            diffusion resistance factor [Dimensionless]. (Default: None).
        moisture_storage_function: Optional list of (relative_humidity,
            water_content) pairs describing the moisture storage curve.
            Relative humidity is between 0 and 1 and water content is in
            kg/m3. (Default: None).
        liquid_transport_suction: Optional list of (water_content [kg/m3],
            liquid transportation coefficient [kg/(m·s·kg/m3)]) pairs for the
            suction direction. (Default: None).
        liquid_transport_redistribution: Optional list of (water_content
            [kg/m3], liquid transportation coefficient) pairs for the
            redistribution direction. (Default: None).
        conductivity_moisture_dependent: Optional list of (water_content
            [kg/m3], thermal conductivity [W/m-K]) pairs. (Default: None).
        conductivity_temperature_dependent: Optional list of (temperature [C],
            thermal conductivity [W/m-K]) pairs. (Default: None).
        diffusion_moisture_dependent: Optional list of (water_content [kg/m3],
            water vapor diffusion resistance factor) pairs. (Default: None).
        enthalpy_temperature_dependent: Optional list of (temperature [C],
            enthalpy [J/kg]) pairs. (Default: None).
        reference_water_content: Optional number for the reference water
            content [kg/m3]. (Default: None).
        free_water_saturation: Optional number for the water content at
            free water saturation [kg/m3]. (Default: None).
        water_absorption_coefficient: Optional number for the water absorption
            coefficient [kg/(m2·s^0.5)]. (Default: None).
        drying_factor: Optional number for the drying factor. (Default: None).
        roughness: Optional text for the surface roughness. Choose from
            'Very Rough', 'Rough', 'Medium Rough', 'Medium Smooth', 'Smooth',
            'Very Smooth'. (Default: None).
        conductivity_moisture_supplement: Optional number for the
            moisture-dependent thermal conductivity supplement [W/m-K per
            kg/m3 of water content]. (Default: None).
        conductivity_temperature_supplement: Optional number for the
            temperature-dependent thermal conductivity supplement [W/m-K-K].
            (Default: None).
        conductivity_design_value: Optional number for the design value of
            thermal conductivity [W/m-K]. (Default: None).
        typical_built_in_moisture: Optional number for the typical built-in
            moisture content [kg/m3]. (Default: None).
        default_thickness: Optional number for the default thickness of the
            material [m]. (Default: None).
        material_information: Optional text string with additional
            information about the material. (Default: None).
        emissivity: Number between 0 and 1 for the infrared hemispherical
            emissivity of the front side of the material. (Default: 0.9).
        emissivity_back: Number between 0 and 1 for the infrared hemispherical
            emissivity of the back side of the material. If None, this will
            default to the same value specified for emissivity. (Default: None)
        reflectance: Optional number between 0 and 1 for the reflectance of solar
            radiation off of the material at normal incidence, averaged over the
            solar spectrum. (Default: None).
        transmittance: Optional number between 0 and 1 for the transmittance of
            solar radiation through the material at normal incidence. (Default: None).
        identifier: Text string for a unique object ID. Must be a UUID in the
            format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx. If None, a UUID will
            automatically be generated. (Default: None).

    Properties:
        * identifier
        * display_name
        * conductivity
        * density
        * porosity
        * specific_heat
        * vapor_diffusion_resistance
        * moisture_storage_function
        * liquid_transport_suction
        * liquid_transport_redistribution
        * conductivity_moisture_dependent
        * conductivity_temperature_dependent
        * diffusion_moisture_dependent
        * enthalpy_temperature_dependent
        * reference_water_content
        * free_water_saturation
        * water_absorption_coefficient
        * drying_factor
        * roughness
        * conductivity_moisture_supplement
        * conductivity_temperature_supplement
        * conductivity_design_value
        * typical_built_in_moisture
        * default_thickness
        * material_information
        * emissivity
        * emissivity_back
        * reflectance
        * transmittance
        * resistivity
        * color
        * protected
        * user_data
    """
    __slots__ = (
        '_conductivity', '_density', '_porosity', '_specific_heat',
        '_vapor_diffusion_resistance', '_moisture_storage_function',
        '_liquid_transport_suction', '_liquid_transport_redistribution',
        '_conductivity_moisture_dependent',
        '_conductivity_temperature_dependent', '_diffusion_moisture_dependent',
        '_enthalpy_temperature_dependent', '_reference_water_content',
        '_free_water_saturation', '_water_absorption_coefficient',
        '_drying_factor', '_roughness', '_conductivity_moisture_supplement',
        '_conductivity_temperature_supplement', '_conductivity_design_value',
        '_typical_built_in_moisture', '_default_thickness',
        '_material_information', '_emissivity', '_emissivity_back',
        '_reflectance', '_transmittance')
    # THERM XML tag for each moisture table property; the value is the
    # (x_name, y_name) pairing that appears in the table docstrings.
    TABLE_TAGS = {
        'moisture_storage_function': 'MoistureStorageFunction',
        'liquid_transport_suction': 'LiquidTransportationCoefficientSuction',
        'liquid_transport_redistribution':
            'LiquidTransportationCoefficientRedistribution',
        'conductivity_moisture_dependent':
            'ThermalConductivityMoistureDependent',
        'diffusion_moisture_dependent':
            'WaterVaporDiffusionResistanceFactorMoistureDependent',
        'conductivity_temperature_dependent':
            'ThermalConductivityTemperatureDependent',
        'enthalpy_temperature_dependent': 'EnthalpyTemperatureDependent'
    }
    # scalar HygroThermal tags in upstream serializer order; values are the
    # corresponding property names on this class. ThermalConductivityDry is
    # always present and is written between SpecificHeatCapacityDry and
    # WaterVaporDiffusionResistanceFactor by _write_hygrothermal.
    SCALAR_TAGS = (
        ('DefaultThickness', 'default_thickness'),
        ('MaterialInformation', 'material_information'),
        ('BulkDensity', 'density'),
        ('Porosity', 'porosity'),
        ('SpecificHeatCapacityDry', 'specific_heat'),
        ('Roughness', 'roughness'),
        ('WaterVaporDiffusionResistanceFactor', 'vapor_diffusion_resistance'),
        ('ReferenceWaterContent', 'reference_water_content'),
        ('FreeWaterSaturation', 'free_water_saturation'),
        ('WaterAbsorptionCoefficient', 'water_absorption_coefficient'),
        ('DryingFactor', 'drying_factor'),
        ('MoistureDependentThermalConductivitySupplement',
         'conductivity_moisture_supplement'),
        ('TypicalBuiltInMoisture', 'typical_built_in_moisture'),
        ('TemperatureDependentThermalConducivitySupplement',
         'conductivity_temperature_supplement'),
        ('ThermalConductivityDesignValue', 'conductivity_design_value')
    )
    ROUGHNESS_TYPES = ('Very Rough', 'Rough', 'Medium Rough', 'Medium Smooth',
                       'Smooth', 'Very Smooth')
    # Allowed children per element of the Solid/Optical subtree, taken from
    # the upstream Materials schema (xs:all groups: at most one occurrence
    # per tag, attributes are never legal). The class models only the
    # Infrared emissivities and the Solar Direct/Front transmittance and
    # reflectance. Schema-legitimate fields without a modeled counterpart
    # (Infrared Transmittance, the Visible range, and Solar Diffuse/Back
    # copies that diverge from the modeled Direct/Front value) are rejected
    # explicitly instead of being silently dropped on write-back; only
    # Solar copies redundant with the modeled value are tolerated, which
    # covers the replicated block the serializer itself emits. Anything
    # outside this grammar is foreign content and is rejected explicitly.
    OPTICAL_GRAMMAR = {
        'Optical': frozenset(('Integrated',)),
        'Integrated': frozenset(('Infrared', 'Solar', 'Visible')),
        'Infrared': frozenset(
            ('Transmittance', 'Emissivity-Front', 'Emissivity-Back')),
        'Solar': frozenset(('Direct', 'Diffuse')),
        'Visible': frozenset(('Direct', 'Diffuse')),
        'Direct': frozenset(('Front', 'Back')),
        'Diffuse': frozenset(('Front', 'Back')),
        'Front': frozenset(('Transmittance', 'Reflectance')),
        'Back': frozenset(('Transmittance', 'Reflectance')),
        'Transmittance': frozenset(),
        'Reflectance': frozenset(),
        'Emissivity-Front': frozenset(),
        'Emissivity-Back': frozenset()
    }
    # modeled leaf path inside the Solar range; every other Solar leaf must
    # carry the same value as this counterpart to be accepted as redundant
    _SOLAR_MODELED_PATH = ('Solar', 'Direct', 'Front')

    def __init__(
        self, conductivity, density=None, porosity=None, specific_heat=None,
        vapor_diffusion_resistance=None, moisture_storage_function=None,
        liquid_transport_suction=None, liquid_transport_redistribution=None,
        conductivity_moisture_dependent=None,
        conductivity_temperature_dependent=None,
        diffusion_moisture_dependent=None,
        enthalpy_temperature_dependent=None,
        reference_water_content=None, free_water_saturation=None,
        water_absorption_coefficient=None, drying_factor=None, roughness=None,
        conductivity_moisture_supplement=None,
        conductivity_temperature_supplement=None,
        conductivity_design_value=None, typical_built_in_moisture=None,
        default_thickness=None, material_information=None,
        emissivity=0.9, emissivity_back=None,
        reflectance=None, transmittance=None, identifier=None
    ):
        """Initialize hygrothermal material."""
        # initialize the identifier and basic properties
        _ThermMaterialBase.__init__(self, identifier)
        # add all of the thermal attributes
        self.conductivity = conductivity
        self.density = density
        self.porosity = porosity
        self.specific_heat = specific_heat
        self.vapor_diffusion_resistance = vapor_diffusion_resistance
        # add all of the moisture transport attributes
        self.moisture_storage_function = moisture_storage_function
        self.liquid_transport_suction = liquid_transport_suction
        self.liquid_transport_redistribution = liquid_transport_redistribution
        self.conductivity_moisture_dependent = conductivity_moisture_dependent
        self.conductivity_temperature_dependent = \
            conductivity_temperature_dependent
        self.diffusion_moisture_dependent = diffusion_moisture_dependent
        self.enthalpy_temperature_dependent = enthalpy_temperature_dependent
        # add the scalar moisture properties
        self.reference_water_content = reference_water_content
        self.free_water_saturation = free_water_saturation
        self.water_absorption_coefficient = water_absorption_coefficient
        self.drying_factor = drying_factor
        self.roughness = roughness
        self.conductivity_moisture_supplement = conductivity_moisture_supplement
        self.conductivity_temperature_supplement = \
            conductivity_temperature_supplement
        self.conductivity_design_value = conductivity_design_value
        self.typical_built_in_moisture = typical_built_in_moisture
        self.default_thickness = default_thickness
        self.material_information = material_information
        # process the optical properties
        self.emissivity = emissivity
        self.emissivity_back = emissivity_back
        self._reflectance = None
        self._transmittance = None
        self.reflectance = reflectance
        self.transmittance = transmittance

    @property
    def conductivity(self):
        """Get or set the dry thermal conductivity of the material [W/m-K]."""
        return self._conductivity

    @conductivity.setter
    def conductivity(self, cond):
        self._conductivity = float_positive(cond, 'material conductivity')
        if self._conductivity == 0:
            raise ValueError('Conductivity cannot be equal to zero.')

    @property
    def density(self):
        """Get or set the bulk density of the material [kg/m3]."""
        return self._density

    @density.setter
    def density(self, value):
        if value is not None:
            value = float_positive(value, 'material density')
        self._density = value

    @property
    def porosity(self):
        """Get or set a number between zero and one for the porosity."""
        return self._porosity

    @porosity.setter
    def porosity(self, value):
        if value is not None:
            value = float_in_range(value, 0.0, 1.0, 'material porosity')
        self._porosity = value

    @property
    def specific_heat(self):
        """Get or set the specific heat capacity of the dry material [J/kg-K]."""
        return self._specific_heat

    @specific_heat.setter
    def specific_heat(self, value):
        if value is not None:
            value = float_positive(value, 'material specific heat')
        self._specific_heat = value

    @property
    def vapor_diffusion_resistance(self):
        """Get or set the water vapor diffusion resistance factor."""
        return self._vapor_diffusion_resistance

    @vapor_diffusion_resistance.setter
    def vapor_diffusion_resistance(self, value):
        if value is not None:
            value = float_positive(value, 'vapor diffusion resistance')
        self._vapor_diffusion_resistance = value

    @property
    def moisture_storage_function(self):
        """Get or set the moisture storage curve as (humidity, water content)."""
        return self._moisture_storage_function

    @moisture_storage_function.setter
    def moisture_storage_function(self, value):
        self._moisture_storage_function = \
            self._checked_table(value, 'moisture storage function', x_max=1)

    @property
    def liquid_transport_suction(self):
        """Get or set the liquid transport coefficient table for suction."""
        return self._liquid_transport_suction

    @liquid_transport_suction.setter
    def liquid_transport_suction(self, value):
        self._liquid_transport_suction = self._checked_table(
            value, 'liquid transport coefficient suction')

    @property
    def liquid_transport_redistribution(self):
        """Get or set the liquid transport coefficient table for redistribution."""
        return self._liquid_transport_redistribution

    @liquid_transport_redistribution.setter
    def liquid_transport_redistribution(self, value):
        self._liquid_transport_redistribution = self._checked_table(
            value, 'liquid transport coefficient redistribution')

    @property
    def conductivity_moisture_dependent(self):
        """Get or set the moisture-dependent thermal conductivity table."""
        return self._conductivity_moisture_dependent

    @conductivity_moisture_dependent.setter
    def conductivity_moisture_dependent(self, value):
        self._conductivity_moisture_dependent = self._checked_table(
            value, 'moisture dependent thermal conductivity', positive_y=True)

    @property
    def conductivity_temperature_dependent(self):
        """Get or set the temperature-dependent thermal conductivity table."""
        return self._conductivity_temperature_dependent

    @conductivity_temperature_dependent.setter
    def conductivity_temperature_dependent(self, value):
        self._conductivity_temperature_dependent = self._checked_table(
            value, 'temperature dependent thermal conductivity',
            x_min=-273.15, positive_y=True)

    @property
    def diffusion_moisture_dependent(self):
        """Get or set the moisture-dependent vapor diffusion resistance table."""
        return self._diffusion_moisture_dependent

    @diffusion_moisture_dependent.setter
    def diffusion_moisture_dependent(self, value):
        self._diffusion_moisture_dependent = self._checked_table(
            value, 'moisture dependent vapor diffusion resistance', positive_y=True)

    @property
    def enthalpy_temperature_dependent(self):
        """Get or set the temperature-dependent enthalpy table."""
        return self._enthalpy_temperature_dependent

    @enthalpy_temperature_dependent.setter
    def enthalpy_temperature_dependent(self, value):
        self._enthalpy_temperature_dependent = self._checked_table(
            value, 'temperature dependent enthalpy', x_min=-273.15, y_min=None)

    @property
    def reference_water_content(self):
        """Get or set the reference water content of the material [kg/m3]."""
        return self._reference_water_content

    @reference_water_content.setter
    def reference_water_content(self, value):
        if value is not None:
            value = float_positive(value, 'reference water content')
        self._reference_water_content = value

    @property
    def free_water_saturation(self):
        """Get or set the water content at free water saturation [kg/m3]."""
        return self._free_water_saturation

    @free_water_saturation.setter
    def free_water_saturation(self, value):
        if value is not None:
            value = float_positive(value, 'free water saturation')
        self._free_water_saturation = value

    @property
    def water_absorption_coefficient(self):
        """Get or set the water absorption coefficient [kg/(m2·s^0.5)]."""
        return self._water_absorption_coefficient

    @water_absorption_coefficient.setter
    def water_absorption_coefficient(self, value):
        if value is not None:
            value = float_positive(value, 'water absorption coefficient')
        self._water_absorption_coefficient = value

    @property
    def drying_factor(self):
        """Get or set the drying factor of the material."""
        return self._drying_factor

    @drying_factor.setter
    def drying_factor(self, value):
        if value is not None:
            value = float_positive(value, 'drying factor')
        self._drying_factor = value

    @property
    def roughness(self):
        """Get or set the surface roughness of the material."""
        return self._roughness

    @roughness.setter
    def roughness(self, value):
        if value is not None:
            clean_input = str(value)
            for key in self.ROUGHNESS_TYPES:
                if key.lower() == clean_input.lower():
                    value = key
                    break
            else:
                raise ValueError(
                    'Material roughness "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.ROUGHNESS_TYPES)))
        self._roughness = value

    @property
    def conductivity_moisture_supplement(self):
        """Get or set the moisture-dependent conductivity supplement."""
        return self._conductivity_moisture_supplement

    @conductivity_moisture_supplement.setter
    def conductivity_moisture_supplement(self, value):
        if value is not None:
            value = float_in_range(
                value, input_name='moisture dependent conductivity supplement')
        self._conductivity_moisture_supplement = value

    @property
    def conductivity_temperature_supplement(self):
        """Get or set the temperature-dependent conductivity supplement."""
        return self._conductivity_temperature_supplement

    @conductivity_temperature_supplement.setter
    def conductivity_temperature_supplement(self, value):
        if value is not None:
            value = float_in_range(
                value,
                input_name='temperature dependent conductivity supplement')
        self._conductivity_temperature_supplement = value

    @property
    def conductivity_design_value(self):
        """Get or set the design value of thermal conductivity [W/m-K]."""
        return self._conductivity_design_value

    @conductivity_design_value.setter
    def conductivity_design_value(self, value):
        if value is not None:
            value = float_positive(value, 'conductivity design value')
        self._conductivity_design_value = value

    @property
    def typical_built_in_moisture(self):
        """Get or set the typical built-in moisture content [kg/m3]."""
        return self._typical_built_in_moisture

    @typical_built_in_moisture.setter
    def typical_built_in_moisture(self, value):
        if value is not None:
            value = float_positive(value, 'typical built-in moisture')
        self._typical_built_in_moisture = value

    @property
    def default_thickness(self):
        """Get or set the default thickness of the material [m]."""
        return self._default_thickness

    @default_thickness.setter
    def default_thickness(self, value):
        if value is not None:
            value = float_positive(value, 'default thickness')
        self._default_thickness = value

    @property
    def material_information(self):
        """Get or set a text string with additional material information."""
        return self._material_information

    @material_information.setter
    def material_information(self, value):
        if value is not None:
            try:
                value = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                pass  # keep it as unicode
        self._material_information = value

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
    def reflectance(self):
        """Get or set the front solar reflectance at normal incidence."""
        return self._reflectance

    @reflectance.setter
    def reflectance(self, s_ref):
        if s_ref is not None:
            s_ref = float_in_range(s_ref, 0.0, 1.0, 'material reflectance')
            if self._transmittance is not None and \
                    s_ref + self._transmittance > 1:
                raise ValueError(
                    'Sum of transmittance and reflectance ({}) is greater '
                    'than 1.'.format(s_ref + self._transmittance))
        self._reflectance = s_ref

    @property
    def transmittance(self):
        """Get or set the solar transmittance at normal incidence."""
        return self._transmittance

    @transmittance.setter
    def transmittance(self, s_tr):
        if s_tr is not None:
            s_tr = float_in_range(s_tr, 0.0, 1.0, 'material transmittance')
            if self._reflectance is not None and \
                    s_tr + self._reflectance > 1:
                raise ValueError(
                    'Sum of transmittance and reflectance ({}) is greater '
                    'than 1.'.format(s_tr + self._reflectance))
        self._transmittance = s_tr

    @property
    def resistivity(self):
        """Get or set the resistivity of the material layer [m-K/W]."""
        return 1 / self._conductivity

    @resistivity.setter
    def resistivity(self, resis):
        self._conductivity = 1 / float_positive(resis, 'material resistivity')

    @classmethod
    def _optical_unknown_fields(cls, element):
        """List foreign tags, duplicates, and attributes in an Optical subtree.

        The grammar is a whitelist, so duplicates of a legitimate tag are
        foreign too: xs:all permits at most one occurrence and .find()
        would silently pick the first.
        """
        unknown = []
        if element.attrib:
            unknown.append('{}/@{}'.format(
                element.tag, ','.join(sorted(element.attrib))))
        seen = set()
        for child in element:
            allowed = cls.OPTICAL_GRAMMAR.get(element.tag, frozenset())
            if child.tag not in allowed or child.tag in seen:
                unknown.append('{}/{}'.format(element.tag, child.tag))
                continue
            seen.add(child.tag)
            unknown.extend(cls._optical_unknown_fields(child))
        return unknown

    @classmethod
    def _optical_unmodeled_values(cls, element):
        """List Optical leaf values this class cannot store on the object.

        The element must already conform to OPTICAL_GRAMMAR. A leaf without
        a modeled counterpart is only tolerated when it is a Solar copy
        carrying the same value as the modeled Solar/Direct/Front leaf,
        so nothing read here is ever silently dropped on write-back. Empty
        leaves carry no value and are never listed.
        """
        unmodeled = []
        integrated = element.find('Integrated')
        if integrated is None:
            return unmodeled
        modeled = {}  # modeled Solar/Direct/Front leaf text per tag
        modeled_path = '/'.join(cls._SOLAR_MODELED_PATH)
        for leaf_tag in ('Transmittance', 'Reflectance'):
            leaf = integrated.find('{}/{}'.format(modeled_path, leaf_tag))
            if leaf is not None:
                modeled[leaf_tag] = leaf.text
        xml_inf = integrated.find('Infrared')
        if xml_inf is not None:
            leaf = xml_inf.find('Transmittance')
            if leaf is not None and leaf.text:
                unmodeled.append(
                    'Integrated/Infrared/Transmittance={}'.format(leaf.text))
        for range_name in ('Solar', 'Visible'):
            xml_range = integrated.find(range_name)
            if xml_range is None:
                continue
            for comp_name in ('Direct', 'Diffuse'):
                xml_comp = xml_range.find(comp_name)
                if xml_comp is None:
                    continue
                for side_name in ('Front', 'Back'):
                    xml_side = xml_comp.find(side_name)
                    if xml_side is None:
                        continue
                    modeled_leaf = (range_name, comp_name, side_name) == \
                        cls._SOLAR_MODELED_PATH
                    for leaf in xml_side:
                        if not leaf.text:
                            continue
                        path = 'Integrated/{}/{}/{}/{}'.format(
                            range_name, comp_name, side_name, leaf.tag)
                        if modeled_leaf:
                            continue  # stored on the object below
                        # a Solar copy is only redundant when it repeats
                        # the modeled Direct/Front value; a missing or
                        # unparseable counterpart cannot be verified
                        try:
                            redundant = range_name == 'Solar' and \
                                leaf.tag in modeled and \
                                float(leaf.text) == float(modeled[leaf.tag])
                        except (TypeError, ValueError):
                            redundant = False
                        if redundant:
                            continue
                        unmodeled.append('{}={}'.format(path, leaf.text))
        return unmodeled

    @staticmethod
    def _checked_table(value, input_name, x_min=0, x_max=None, y_min=0,
                       positive_y=False):
        """Check a moisture or temperature table and return it as a tuple."""
        if value is None:
            return None
        if not isinstance(value, (list, tuple)):
            raise ValueError(
                'THMZ-E2004: Expected a list of (x, y) pairs for {}. Got {}.'.format(
                    input_name, type(value)))
        if len(value) < 1:
            raise ValueError(
                'THMZ-E2004: {} table requires at least one point.'.format(input_name))
        table = []
        for pair in value:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise ValueError(
                    'THMZ-E2004: Expected (x, y) pairs for {}. Got {}.'.format(
                        input_name, pair))
            try:
                x, y = float(pair[0]), float(pair[1])
            except (TypeError, ValueError, OverflowError):
                raise ValueError(
                    'THMZ-E2004: {} table requires numeric x and y.'.format(input_name))
            if math.isinf(x) or math.isnan(x) or math.isinf(y) or math.isnan(y):
                raise ValueError(
                    'THMZ-E2004: {} table requires finite x and y.'.format(input_name))
            if x < x_min or (x_max is not None and x > x_max) or \
                    (y_min is not None and y < y_min) or (positive_y and y <= 0):
                raise ValueError(
                    'THMZ-E2004: {} table pair {} is outside its physical '
                    'domain.'.format(input_name, pair))
            table.append((x, y))
        xs = [pair[0] for pair in table]
        if not all(a < b for a, b in zip(xs, xs[1:])):
            raise ValueError(
                'THMZ-E2004: {} table x values must be strictly increasing.'.format(
                    input_name))
        return tuple(table)

    def _write_hygrothermal(self, xml_hyt):
        """Write the full HygroThermal record into a Solid element."""
        for tag, prop in self.SCALAR_TAGS:
            value = getattr(self, prop)
            if value is not None:
                xml_scalar = ET.SubElement(xml_hyt, tag)
                xml_scalar.text = str(value)
            if tag == 'SpecificHeatCapacityDry':  # required conductivity slot
                xml_cond = ET.SubElement(xml_hyt, 'ThermalConductivityDry')
                xml_cond.text = str(self.conductivity)
        for prop, tag in self.TABLE_TAGS.items():
            table = getattr(self, prop)
            if table is not None:
                xml_table = ET.SubElement(xml_hyt, tag)
                for x, y in table:
                    xml_value = ET.SubElement(xml_table, 'TableValue')
                    xml_x = ET.SubElement(xml_value, 'x')
                    xml_x.text = str(x)
                    xml_y = ET.SubElement(xml_value, 'y')
                    xml_y.text = str(y)

    @classmethod
    def from_therm_xml(cls, xml_element):
        """Create a HygrothermalMaterial from an XML element of a THERM Material.

        Args:
            xml_element: An XML element of a THERM material.

        Raises:
            ValueError: The HygroThermal record carries fields this class
                does not model, including content nested inside the
                moisture tables and inside the x/y and scalar leaves,
                attributes on modeled elements, or a TableValue without
                exactly one x and one y leaf carrying text. Also raised
                for foreign children, duplicates, or attributes on Solid,
                and for Optical content outside the schema grammar
                (OPTICAL_GRAMMAR). Schema-legitimate optical values this
                class does not model are also rejected: the Infrared
                Transmittance, every Visible value, and Solar Diffuse/Back
                copies diverging from the modeled Solar/Direct/Front
                value. Only Solar copies redundant with the modeled
                value and valueless elements are tolerated.
        """
        # create the base material from the UUID and conductivity
        name = xml_element.findtext('Name') or \
            xml_element.findtext('UUID') or '<unnamed>'
        xml_uuid = xml_element.find('UUID')
        if xml_uuid is None or xml_uuid.text is None:
            raise ValueError(
                'Material "{}" lacks the required UUID element.'
                .format(name))
        identifier = xml_uuid.text
        if len(identifier) == 31:
            identifier = uuid_from_therm_id(identifier)
        xml_solid = xml_element.find('Solid')
        xml_hyt = xml_solid.find('HygroThermal') \
            if xml_solid is not None else None
        if xml_hyt is None:
            raise ValueError(
                'Material "{}" lacks a Solid/HygroThermal record.'
                .format(name))
        # reject foreign children or attributes on Solid itself; the Solid
        # grammar is only HygroThermal plus Optical in this record
        solid_foreign = [child.tag for child in xml_solid
                         if child.tag not in ('HygroThermal', 'Optical')]
        if xml_solid.attrib:
            solid_foreign.append('@{}'.format(
                ','.join(sorted(xml_solid.attrib))))
        solid_tags = [child.tag for child in xml_solid]
        solid_foreign.extend('{} (duplicate)'.format(tag)
                             for tag in ('HygroThermal', 'Optical')
                             if solid_tags.count(tag) > 1)
        if solid_foreign:
            raise ValueError(
                'Material "{}" has unsupported Solid fields: {}.'
                .format(name, ', '.join(solid_foreign)))
        # reject HygroThermal content this class does not model instead of
        # silently dropping it: unknown direct children, elements nested
        # inside the moisture tables or inside the x/y and scalar leaves,
        # and attributes on any modeled element. The extractor performs
        # only a direct-children scan, so the deeper checks live here.
        unknown = [child.tag for child in xml_hyt
                   if child.tag not in cls.TABLE_TAGS.values()
                   and child.tag not in dict(cls.SCALAR_TAGS)
                   and child.tag != 'ThermalConductivityDry']
        if xml_hyt.attrib:
            unknown.append('@{}'.format(
                ','.join(sorted(xml_hyt.attrib))))
        scalar_set = set(dict(cls.SCALAR_TAGS)) | {'ThermalConductivityDry'}
        seen = set()
        for child in xml_hyt:
            if child.tag in seen:
                raise ValueError(
                    'THMZ-E2002: Material "{}" has duplicate '
                    'Solid/HygroThermal/{}.'.format(name, child.tag))
            seen.add(child.tag)
            if child.attrib:
                unknown.append('{}/@{}'.format(
                    child.tag, ','.join(sorted(child.attrib))))
            if child.tag in scalar_set:
                unknown.extend('{}/{}'.format(child.tag, leaf.tag)
                               for leaf in child)
            elif child.tag in cls.TABLE_TAGS.values():
                for item in child:
                    if item.tag != 'TableValue':
                        unknown.append('{}/{}'.format(child.tag, item.tag))
                        continue
                    if item.attrib:
                        unknown.append('{}/TableValue/@{}'.format(
                            child.tag, ','.join(sorted(item.attrib))))
                    for field in item:
                        if field.tag not in ('x', 'y'):
                            unknown.append('{}/TableValue/{}'.format(
                                child.tag, field.tag))
                            continue
                        if field.attrib:
                            unknown.append('{}/TableValue/{}/@{}'.format(
                                child.tag, field.tag,
                                ','.join(sorted(field.attrib))))
                        unknown.extend('{}/TableValue/{}/{}'.format(
                            child.tag, field.tag, leaf.tag)
                            for leaf in field)
        if unknown:
            raise ValueError(
                'Material "{}" has unsupported HygroThermal fields: {}.'
                .format(name, ', '.join(unknown)))
        conductivity = xml_hyt.findtext('ThermalConductivityDry')
        if conductivity is None or not conductivity.strip():
            raise ValueError(
                'THMZ-E2003: Material "{}" lacks '
                'Solid/HygroThermal/ThermalConductivityDry.'.format(name))
        mat = cls(conductivity, identifier=identifier)
        # assign the scalar hygrothermal attributes if specified
        for tag, prop in cls.SCALAR_TAGS:
            xml_scalar = xml_hyt.find(tag)
            if xml_scalar is not None:
                setattr(mat, prop, xml_scalar.text)
        # assign the moisture tables if specified; every TableValue must
        # carry exactly one x leaf and one y leaf with parseable text
        for prop, tag in cls.TABLE_TAGS.items():
            xml_table = xml_hyt.find(tag)
            if xml_table is not None:
                pairs = []
                for item in xml_table.findall('TableValue'):
                    for leaf_tag in ('x', 'y'):
                        leaves = item.findall(leaf_tag)
                        if len(leaves) != 1 or not leaves[0].text:
                            raise ValueError(
                                'Material "{}" has a TableValue in {} '
                                'without exactly one {} leaf carrying '
                                'text.'.format(name, tag, leaf_tag))
                    pairs.append(
                        (float(item.findtext('x')),
                         float(item.findtext('y'))))
                setattr(mat, prop, tuple(pairs))
        # assign the optical properties if specified; first reject any
        # Optical content outside the schema grammar so foreign fields
        # cannot be silently dropped by the targeted finds below, then
        # reject schema-legitimate values this class cannot store so they
        # are never silently lost on write-back
        xml_optical = xml_solid.find('Optical')
        if xml_optical is not None:
            opt_unknown = cls._optical_unknown_fields(xml_optical)
            if opt_unknown:
                raise ValueError(
                    'Material "{}" has unsupported Optical fields: {}.'
                    .format(name, ', '.join(opt_unknown)))
            opt_unmodeled = cls._optical_unmodeled_values(xml_optical)
            if opt_unmodeled:
                raise ValueError(
                    'Material "{}" has unmodeled Optical values: {}. This '
                    'class models only the Infrared emissivities and the '
                    'Solar/Direct/Front transmittance and reflectance.'
                    .format(name, ', '.join(opt_unmodeled)))
            xml_int = xml_optical.find('Integrated')
            if xml_int is not None:
                xml_inf = xml_int.find('Infrared')
                if xml_inf is not None:
                    xml_emiss = xml_inf.find('Emissivity-Front')
                    if xml_emiss is not None:
                        mat.emissivity = xml_emiss.text
                    xml_emiss_b = xml_inf.find('Emissivity-Back')
                    if xml_emiss_b is not None:
                        mat.emissivity_back = xml_emiss_b.text
                xml_sol = xml_int.find('Solar')
                if xml_sol is not None:
                    xml_dir = xml_sol.find('Direct')
                    if xml_dir is not None:
                        xml_front = xml_dir.find('Front')
                        if xml_front is not None:
                            xml_trans = xml_front.find('Transmittance')
                            if xml_trans is not None:
                                mat.transmittance = xml_trans.text
                            xml_ref = xml_front.find('Reflectance')
                            if xml_ref is not None:
                                mat.reflectance = xml_ref.text
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
    def from_therm_xml_str(cls, xml_str):
        """Create a HygrothermalMaterial from an XML text string of a THERM Material.

        Args:
            xml_str: An XML text string of a THERM material.
        """
        root = ET.fromstring(xml_str)
        return cls.from_therm_xml(root)

    @classmethod
    def from_dict(cls, data):
        """Create a HygrothermalMaterial from a dictionary.

        Args:
            data: A python dictionary in the following format

        .. code-block:: python

            {
            "type": 'HygrothermalMaterial',
            "identifier": 'f26f3597-e3ee-43fe-a0b3-ec673f993d86',
            "display_name": 'Brick',
            "conductivity": 0.62,
            "density": 1700,
            "specific_heat": 840,
            "vapor_diffusion_resistance": 38,
            "moisture_storage_function": [[0.0, 0.0], [0.95, 60.0],
                [1.0, 400.0]],
            "liquid_transport_suction": [[0.0, 0.0], [60.0, 1e-6]],
            "emissivity": 0.9
            }
        """
        if data['type'] != 'HygrothermalMaterial':
            raise ValueError(
                'Expected HygrothermalMaterial. Got {}.'.format(data['type']))

        scalar_props = ('density', 'porosity', 'specific_heat',
                        'vapor_diffusion_resistance', 'reference_water_content',
                        'free_water_saturation', 'water_absorption_coefficient',
                        'drying_factor', 'roughness',
                        'conductivity_moisture_supplement',
                        'conductivity_temperature_supplement',
                        'conductivity_design_value', 'typical_built_in_moisture',
                        'default_thickness', 'material_information')
        table_props = cls.TABLE_TAGS.keys()
        kwargs = {'identifier': data.get('identifier')}
        for prop in scalar_props:
            if prop in data:
                kwargs[prop] = data[prop]
        for prop in table_props:
            if prop in data:
                kwargs[prop] = data[prop]
        if 'emissivity' in data and data['emissivity'] is not None:
            kwargs['emissivity'] = data['emissivity']
        if 'emissivity_back' in data:
            kwargs['emissivity_back'] = data['emissivity_back']
        if 'reflectance' in data:
            kwargs['reflectance'] = data['reflectance']
        if 'transmittance' in data:
            kwargs['transmittance'] = data['transmittance']
        new_mat = cls(data['conductivity'], **kwargs)
        if 'display_name' in data and data['display_name'] is not None:
            new_mat.display_name = data['display_name']
        if 'color' in data and data['color'] is not None:
            new_mat.color = data['color']
        if 'protected' in data and data['protected'] is not None:
            new_mat.protected = data['protected']
        if 'user_data' in data and data['user_data'] is not None:
            new_mat.user_data = data['user_data']
        return new_mat

    def to_therm_xml(self, materials_element=None):
        """Get an THERM XML element of the material.

        Args:
            materials_element: An optional XML Element for the Materials to
                which the generated objects will be added. If None, a new XML
                Element will be generated.

        .. code-block:: xml

            <Material>
                <UUID>1543f77f-e4aa-47d4-b7bf-2365d7bc0b9d</UUID>
                <Name>Brick</Name>
                <Protected>false</Protected>
                <Color>0xFFFFC1</Color>
                <Solid>
                    <HygroThermal>
                        <ThermalConductivityDry>0.62</ThermalConductivityDry>
                        <MoistureStorageFunction>
                            <TableValue><x>0</x><y>0</y></TableValue>
                        </MoistureStorageFunction>
                    </HygroThermal>
                    <Optical>
                        <Integrated>
                            <Infrared>
                                <Emissivity-Front>0.9</Emissivity-Front>
                                <Emissivity-Back>0.9</Emissivity-Back>
                            </Infrared>
                        </Integrated>
                    </Optical>
                </Solid>
            </Material>
        """
        # create a new Materials element if one is not specified
        if materials_element is not None:
            xml_mat = ET.SubElement(materials_element, 'Material')
        else:
            xml_mat = ET.Element('Material')
        # add all of the required basic attributes
        xml_id = ET.SubElement(xml_mat, 'UUID')
        xml_id.text = self.identifier
        xml_name = ET.SubElement(xml_mat, 'Name')
        xml_name.text = self.display_name
        xml_protect = ET.SubElement(xml_mat, 'Protected')
        xml_protect.text = 'true' if self.protected else 'false'
        xml_color = ET.SubElement(xml_mat, 'Color')
        xml_color.text = self.color.to_hex().replace('#', '0x')
        xml_solid = ET.SubElement(xml_mat, 'Solid')
        # add the hygrothermal and optical attributes
        xml_hyt = ET.SubElement(xml_solid, 'HygroThermal')
        self._write_hygrothermal(xml_hyt)
        xml_optical = ET.SubElement(xml_solid, 'Optical')
        xml_int = ET.SubElement(xml_optical, 'Integrated')
        xml_inf = ET.SubElement(xml_int, 'Infrared')
        xml_emiss = ET.SubElement(xml_inf, 'Emissivity-Front')
        xml_emiss.text = str(self.emissivity)
        xml_emiss_b = ET.SubElement(xml_inf, 'Emissivity-Back')
        xml_emiss_b.text = str(self.emissivity_back)
        if self.reflectance is not None or self.transmittance is not None:
            ref = '0' if self.reflectance is None else str(self.reflectance)
            trans = '0' if self.transmittance is None else str(self.transmittance)
            xml_sol = ET.SubElement(xml_int, 'Solar')
            for sol_comp in ('Direct', 'Diffuse'):
                xml_sol_comp = ET.SubElement(xml_sol, sol_comp)
                for mat_side in ('Front', 'Back'):
                    xml_comp_s = ET.SubElement(xml_sol_comp, mat_side)
                    xml_comp_s_t = ET.SubElement(xml_comp_s, 'Transmittance')
                    xml_comp_s_t.text = trans
                    xml_comp_s_r = ET.SubElement(xml_comp_s, 'Reflectance')
                    xml_comp_s_r.text = ref
        return xml_mat

    def to_therm_xml_str(self):
        """Get an THERM XML string of the material."""
        xml_root = self.to_therm_xml()
        try:  # try to indent the XML to make it read-able
            ET.indent(xml_root)
            return ET.tostring(xml_root, encoding='unicode')
        except AttributeError:  # we are in Python 2 and no indent is available
            return ET.tostring(xml_root)

    def to_dict(self):
        """HygrothermalMaterial dictionary representation."""
        base = {
            'type': 'HygrothermalMaterial',
            'identifier': self.identifier,
            'conductivity': self.conductivity,
            'emissivity': self.emissivity
        }
        for tag, prop in self.SCALAR_TAGS:
            if getattr(self, prop) is not None:
                base[prop] = getattr(self, prop)
        for prop in self.TABLE_TAGS:
            if getattr(self, prop) is not None:
                base[prop] = [list(pair) for pair in getattr(self, prop)]
        if self._emissivity_back is not None:
            base['emissivity_back'] = self._emissivity_back
        if self._reflectance is not None:
            base['reflectance'] = self.reflectance
        if self._transmittance is not None:
            base['transmittance'] = self.transmittance
        if self._display_name is not None:
            base['display_name'] = self.display_name
        base['protected'] = self._protected
        base['color'] = self.color.to_hex()
        if self._user_data is not None:
            base['user_data'] = self.user_data
        return base

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (self.identifier, self.conductivity, self.density,
                self.porosity, self.specific_heat,
                self.vapor_diffusion_resistance,
                self.moisture_storage_function, self.liquid_transport_suction,
                self.liquid_transport_redistribution,
                self.conductivity_moisture_dependent,
                self.conductivity_temperature_dependent,
                self.diffusion_moisture_dependent,
                self.enthalpy_temperature_dependent,
                self.reference_water_content, self.free_water_saturation,
                self.water_absorption_coefficient, self.drying_factor,
                self.roughness, self.conductivity_moisture_supplement,
                self.conductivity_temperature_supplement,
                self.conductivity_design_value, self.typical_built_in_moisture,
                self.default_thickness, self.material_information,
                self.emissivity, self.emissivity_back,
                self.reflectance, self.transmittance)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, HygrothermalMaterial) and \
            self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        new_material = self.__class__(
            self.conductivity, self._density, self._porosity, self._specific_heat,
            self._vapor_diffusion_resistance, self._moisture_storage_function,
            self._liquid_transport_suction,
            self._liquid_transport_redistribution,
            self._conductivity_moisture_dependent,
            self._conductivity_temperature_dependent,
            self._diffusion_moisture_dependent,
            self._enthalpy_temperature_dependent,
            self._reference_water_content, self._free_water_saturation,
            self._water_absorption_coefficient, self._drying_factor,
            self._roughness, self._conductivity_moisture_supplement,
            self._conductivity_temperature_supplement,
            self._conductivity_design_value, self._typical_built_in_moisture,
            self._default_thickness, self._material_information,
            self._emissivity, self._emissivity_back,
            self._reflectance, self._transmittance, self.identifier)
        new_material._display_name = self._display_name
        new_material._color = self._color
        new_material._protected = self._protected
        new_material._user_data = None if self._user_data is None \
            else self._user_data.copy()
        return new_material

    def __repr__(self):
        return 'Hygrothermal THERM Material: {}'.format(self.display_name)
