# coding=utf-8
"""Transient calculation parameters."""
from __future__ import division
import xml.etree.ElementTree as ET

from fairyfly.typing import float_in_range, float_positive, int_positive


class TransientCalculation(object):
    """Transient calculation parameters for a THERM simulation.

    This object mirrors the transient portion of a THERM
    ``Properties/CalculationOptions`` record: the calculation mode, engine
    parameters, transient methodology and the constant initial conditions.
    The schema ``Values from input file`` methodology is not implemented by
    the data layer serializer mapping and is rejected (THMZ-E2000).

    Args:
        time_range: Optional number for the total duration of the simulation
            in seconds. When specified it must be an exact multiple of
            timestep and it overrides the default number_of_timesteps.
            (Default: None).
        timestep: A positive number for the duration of a single timestep
            in seconds. (Default: 3600).
        number_of_timesteps: Optional positive integer for the number of
            timesteps the solver runs. If both time_range and
            number_of_timesteps are given they must agree.
            (Default: 8670).
        initial_temperature: A number for the constant initial temperature
            assigned to every node [C]. Used when methodology is
            'Constant everywhere'. (Default: 21).
        initial_humidity: A number between 0 and 1 for the constant initial
            relative humidity assigned to every node. Used when methodology
            is 'Constant everywhere'. (Default: 0.5).
        methodology: Text for the transient calculation methodology. Choose
            from 'Constant everywhere' or 'Use first timestep'.
            (Default: 'Constant everywhere').
        simulate_moisture: Boolean for whether moisture is simulated together
            with thermal transport. (Default: False).
        convergence_tolerance: A positive number for the engine convergence
            tolerance. (Default: 1e-5).
        relaxation_parameter: A positive number for the engine relaxation
            parameter. (Default: 1).

    Properties:
        * time_range
        * timestep
        * number_of_timesteps
        * initial_temperature
        * initial_humidity
        * methodology
        * simulate_moisture
        * convergence_tolerance
        * relaxation_parameter
    """
    __slots__ = ('_timestep', '_number_of_timesteps', '_initial_temperature',
                 '_initial_humidity', '_methodology', '_simulate_moisture',
                 '_convergence_tolerance', '_relaxation_parameter',
                 '_modeling_options')
    METHODOLOGIES = ('Constant everywhere', 'Use first timestep')
    ENGINE = 'HygroThermFEM'  # Conrad supports steady-state thermal only
    _MODELING_OPTION_TAGS = (
        ('exclude_liquid_transport', 'ExcludeWaterLiquidTransportation', True),
        ('exclude_evaporation_heat', 'ExcludeHeatOfEvaporation', True),
        ('exclude_capillary_conduction', 'ExcludeCapillaryConduction', True),
        ('exclude_vapor_conduction', 'ExcludeVaporDiffusionConduction', True),
        ('exclude_fusion_heat', 'ExcludeLatentHeatOfFusion', True),
    )

    def __init__(
        self, time_range=None, timestep=3600, number_of_timesteps=None,
        initial_temperature=21, initial_humidity=0.5,
        methodology='Constant everywhere', simulate_moisture=False,
        convergence_tolerance=1e-5, relaxation_parameter=1,
        modeling_options=None
    ):
        """Initialize TransientCalculation."""
        self.timestep = timestep
        if time_range is not None:
            steps = float_positive(time_range, 'transient time range') / \
                self._timestep
            rounded = round(steps)
            if abs(steps - rounded) > 1e-9:
                raise ValueError(
                    'Transient time_range {} s is not an exact multiple of '
                    'timestep {} s.'.format(time_range, self._timestep))
            if number_of_timesteps is not None:
                if int_positive(
                        number_of_timesteps, 'number of timesteps') != rounded:
                    raise ValueError(
                        'Transient time_range/timestep and number_of_timesteps '
                        'do not agree ({} vs {}).'.format(
                            rounded, number_of_timesteps))
            self._number_of_timesteps = rounded
        elif number_of_timesteps is not None:
            self._number_of_timesteps = int_positive(
                number_of_timesteps, 'number of timesteps')
        else:
            self._number_of_timesteps = 8670
        self.initial_temperature = initial_temperature
        self.initial_humidity = initial_humidity
        self.methodology = methodology
        self.simulate_moisture = simulate_moisture
        self.convergence_tolerance = convergence_tolerance
        self.relaxation_parameter = relaxation_parameter
        self.modeling_options = modeling_options

    @property
    def time_range(self):
        """Get the total duration of the simulation in seconds."""
        return self._timestep * self._number_of_timesteps

    @property
    def timestep(self):
        """Get or set the duration of a single timestep in seconds."""
        return self._timestep

    @timestep.setter
    def timestep(self, value):
        self._timestep = float_positive(value, 'transient timestep')

    @property
    def number_of_timesteps(self):
        """Get or set the number of timesteps the solver runs."""
        return self._number_of_timesteps

    @number_of_timesteps.setter
    def number_of_timesteps(self, value):
        self._number_of_timesteps = int_positive(value, 'number of timesteps')

    @property
    def initial_temperature(self):
        """Get or set the constant initial temperature of every node [C]."""
        return self._initial_temperature

    @initial_temperature.setter
    def initial_temperature(self, value):
        self._initial_temperature = float_in_range(
            value, mi=-273.15, input_name='initial temperature')

    @property
    def initial_humidity(self):
        """Get or set the constant initial relative humidity of every node."""
        return self._initial_humidity

    @initial_humidity.setter
    def initial_humidity(self, value):
        self._initial_humidity = float_in_range(
            value, 0.0, 1.0, 'initial humidity')

    @property
    def methodology(self):
        """Get or set the transient calculation methodology."""
        return self._methodology

    @methodology.setter
    def methodology(self, value):
        if value is not None:
            clean_input = str(value)
            if clean_input.lower() == 'values from input file':
                raise ValueError(
                    'THMZ-E2000: "Values from input file" is not supported; '
                    'the data layer serializer has no mapping for it.\n'
                    'Choose from the following:\n{}'.format(
                        '\n'.join(self.METHODOLOGIES)))
            for key in self.METHODOLOGIES:
                if key.lower() == clean_input.lower():
                    value = key
                    break
            else:
                raise ValueError(
                    'TransientCalculation methodology "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.METHODOLOGIES)))
            self._methodology = value
        else:
            self._methodology = self.METHODOLOGIES[0]

    @property
    def simulate_moisture(self):
        """Get or set whether moisture transport is simulated."""
        return self._simulate_moisture

    @simulate_moisture.setter
    def simulate_moisture(self, value):
        self._simulate_moisture = bool(value)

    @property
    def convergence_tolerance(self):
        """Get or set the engine convergence tolerance."""
        return self._convergence_tolerance

    @convergence_tolerance.setter
    def convergence_tolerance(self, value):
        self._convergence_tolerance = float_positive(
            value, 'convergence tolerance')

    @property
    def relaxation_parameter(self):
        """Get or set the engine relaxation parameter."""
        return self._relaxation_parameter

    @relaxation_parameter.setter
    def relaxation_parameter(self, value):
        self._relaxation_parameter = float_positive(
            value, 'relaxation parameter')

    @property
    def modeling_options(self):
        """Get or set optional hygrothermal ModelingOptions overrides."""
        return dict(self._modeling_options) if self._modeling_options is not None else None

    @modeling_options.setter
    def modeling_options(self, value):
        if value is None:
            self._modeling_options = None
            return
        if not isinstance(value, dict):
            raise TypeError(
                'modeling_options must be a dict or None, got {}.'.format(
                    type(value).__name__))
        defaults = {
            key: default for key, _, default in self._MODELING_OPTION_TAGS
        }
        defaults['variable_conductivity'] = False
        unknown = set(value) - set(defaults)
        if unknown:
            raise ValueError(
                'Unsupported modeling_options key(s): {}'.format(
                    ', '.join(sorted(unknown))))
        normalized = dict(defaults)
        for key, flag in value.items():
            normalized[key] = bool(flag)
        self._modeling_options = normalized

    @staticmethod
    def _required(calculation_element, tag):
        """Get a CalculationOptions child, creating it when absent."""
        xml_child = calculation_element.find(tag)
        if xml_child is None:
            xml_child = ET.SubElement(calculation_element, tag)
        return xml_child

    def to_therm_xml(self, calculation_element=None):
        """Apply the transient options to a CalculationOptions element.

        Args:
            calculation_element: An optional XML Element for the
                CalculationOptions whose transient fields will be set. If None,
                a new XML Element will be generated. (Default: None).

        .. code-block:: xml

            <CalculationOptions>
                <SimulationEngine>HygroThermFEM</SimulationEngine>
                <CalculationMode>Transient</CalculationMode>
                <SimulateMoisture>false</SimulateMoisture>
                <SimulateThermal>true</SimulateThermal>
                <TransientCalculationMethodology>
                    Constant everywhere
                </TransientCalculationMethodology>
                <ConstantInitialConditionsTransient>
                    <Temperature>21</Temperature>
                    <Humidity>0.5</Humidity>
                </ConstantInitialConditionsTransient>
                <EngineParameters>
                    <ConvergenceTolerance>1e-05</ConvergenceTolerance>
                    <RelaxationParameter>1</RelaxationParameter>
                    <TimeStep>3600</TimeStep>
                    <NumberOfTimesteps>8670</NumberOfTimesteps>
                </EngineParameters>
            </CalculationOptions>
        """
        if calculation_element is not None:
            xml_opt = calculation_element
        else:
            xml_opt = ET.Element('CalculationOptions')
        self._required(xml_opt, 'SimulationEngine').text = self.ENGINE
        self._required(xml_opt, 'CalculationMode').text = 'Transient'
        self._required(xml_opt, 'SimulateMoisture').text = \
            'true' if self.simulate_moisture else 'false'
        self._required(xml_opt, 'SimulateThermal').text = 'true'
        xml_modeling = xml_opt.find('ModelingOptions')
        if self.simulate_moisture and self._modeling_options is not None:
            if xml_modeling is None:
                xml_modeling = ET.SubElement(xml_opt, 'ModelingOptions')
            for key, tag, _ in self._MODELING_OPTION_TAGS:
                self._required(xml_modeling, tag).text = (
                    'true' if self._modeling_options[key] else 'false')
            exclude_var = (
                'false' if self._modeling_options['variable_conductivity']
                else 'true')
            self._required(
                xml_modeling, 'ExcludeThermalConductivityMoistureDependent'
            ).text = exclude_var
            self._required(
                xml_modeling, 'ExcludeThermalConductivityTemperatureDependent'
            ).text = exclude_var
        elif not self.simulate_moisture and xml_modeling is not None:
            for _, tag, _ in self._MODELING_OPTION_TAGS:
                self._required(xml_modeling, tag).text = 'true'
            self._required(
                xml_modeling, 'ExcludeThermalConductivityMoistureDependent'
            ).text = 'true'
            self._required(
                xml_modeling, 'ExcludeThermalConductivityTemperatureDependent'
            ).text = 'true'
        self._required(xml_opt, 'TransientCalculationMethodology').text = \
            self.methodology
        xml_init = self._required(xml_opt, 'ConstantInitialConditionsTransient')
        self._required(xml_init, 'Temperature').text = \
            str(self.initial_temperature)
        self._required(xml_init, 'Humidity').text = str(self.initial_humidity)
        xml_engine = self._required(xml_opt, 'EngineParameters')
        self._required(xml_engine, 'ConvergenceTolerance').text = \
            str(self.convergence_tolerance)
        self._required(xml_engine, 'RelaxationParameter').text = \
            str(self.relaxation_parameter)
        self._required(xml_engine, 'TimeStep').text = str(self.timestep)
        self._required(xml_engine, 'NumberOfTimesteps').text = \
            str(self.number_of_timesteps)
        return xml_opt

    def to_therm_xml_str(self):
        """Get an THERM XML string of the transient calculation options."""
        xml_root = self.to_therm_xml()
        try:  # try to indent the XML to make it read-able
            ET.indent(xml_root)
            return ET.tostring(xml_root, encoding='unicode')
        except AttributeError:  # we are in Python 2 and no indent is available
            return ET.tostring(xml_root)

    @classmethod
    def from_therm_xml(cls, xml_element):
        """Create TransientCalculation from a CalculationOptions element.

        Args:
            xml_element: An XML element of a THERM CalculationOptions record.
        """
        if xml_element.tag == 'CalculationOptions':
            xml_opt = xml_element
        else:
            xml_opt = xml_element.find('CalculationOptions')
        if xml_opt is None:
            raise ValueError('Expected a CalculationOptions element.')
        if xml_opt.findtext('CalculationMode') != 'Transient':
            raise ValueError(
                'CalculationMode "{}" is not Transient.'.format(
                    xml_opt.findtext('CalculationMode')))
        xml_init = xml_opt.find('ConstantInitialConditionsTransient')
        init_temp = xml_init.findtext('Temperature') if xml_init is not None \
            else 21
        init_hum = xml_init.findtext('Humidity') if xml_init is not None \
            else 0.5
        xml_engine = xml_opt.find('EngineParameters')
        tolerance = relaxation = timestep = n_steps = None
        if xml_engine is not None:
            tolerance = xml_engine.findtext('ConvergenceTolerance')
            relaxation = xml_engine.findtext('RelaxationParameter')
            timestep = xml_engine.findtext('TimeStep')
            n_steps = xml_engine.findtext('NumberOfTimesteps')
        moisture = xml_opt.findtext('SimulateMoisture') == 'true'
        modeling_options = None
        xml_modeling = xml_opt.find('ModelingOptions')
        if moisture and xml_modeling is not None:
            parsed = {}
            for key, tag, default in cls._MODELING_OPTION_TAGS:
                text = xml_modeling.findtext(tag)
                parsed[key] = default if text is None else (text.lower() == 'true')
            m_dep = xml_modeling.findtext('ExcludeThermalConductivityMoistureDependent')
            t_dep = xml_modeling.findtext('ExcludeThermalConductivityTemperatureDependent')
            var_cond = (
                (m_dep is not None and m_dep.lower() == 'false')
                or (t_dep is not None and t_dep.lower() == 'false')
            )
            parsed['variable_conductivity'] = var_cond
            defaults = {k: d for k, _, d in cls._MODELING_OPTION_TAGS}
            defaults['variable_conductivity'] = False
            if parsed != defaults:
                modeling_options = parsed
        kwargs = {}
        if tolerance is not None:
            kwargs['convergence_tolerance'] = tolerance
        if relaxation is not None:
            kwargs['relaxation_parameter'] = relaxation
        if timestep is not None:
            kwargs['timestep'] = timestep
        if n_steps is not None:
            kwargs['number_of_timesteps'] = n_steps
        return cls(
            initial_temperature=init_temp, initial_humidity=init_hum,
            methodology=xml_opt.findtext('TransientCalculationMethodology'),
            simulate_moisture=moisture,
            modeling_options=modeling_options, **kwargs)

    @classmethod
    def from_therm_xml_str(cls, xml_str):
        """Create a TransientCalculation from an XML text string.

        Args:
            xml_str: An XML text string of a THERM CalculationOptions record.
        """
        return cls.from_therm_xml(ET.fromstring(xml_str))

    @classmethod
    def from_dict(cls, data):
        """Create a TransientCalculation object from a dictionary.

        Args:
            data: A TransientCalculation dictionary in the format below.

        .. code-block:: python

            {
            "type": 'TransientCalculation',
            "time_range": 31536000,
            "timestep": 3600,
            "initial_temperature": 21,
            "initial_humidity": 0.5,
            "methodology": 'Constant everywhere',
            "simulate_moisture": False
            }
        """
        if data['type'] != 'TransientCalculation':
            raise ValueError(
                'Expected TransientCalculation. Got {}.'.format(data['type']))
        kwargs = {}
        for key in ('time_range', 'timestep', 'number_of_timesteps',
                    'initial_temperature', 'initial_humidity', 'methodology',
                    'simulate_moisture', 'convergence_tolerance',
                    'relaxation_parameter', 'modeling_options'):
            if key in data and data[key] is not None:
                kwargs[key] = data[key]
        return cls(**kwargs)

    def to_dict(self):
        """TransientCalculation dictionary representation."""
        data = {
            'type': 'TransientCalculation',
            'time_range': self.time_range,
            'timestep': self.timestep,
            'number_of_timesteps': self.number_of_timesteps,
            'initial_temperature': self.initial_temperature,
            'initial_humidity': self.initial_humidity,
            'methodology': self.methodology,
            'simulate_moisture': self.simulate_moisture,
            'convergence_tolerance': self.convergence_tolerance,
            'relaxation_parameter': self.relaxation_parameter
        }
        if self._modeling_options is not None:
            data['modeling_options'] = dict(self._modeling_options)
        return data

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        modeling_key = (
            tuple(sorted(self._modeling_options.items()))
            if self._modeling_options is not None else None
        )
        return (self.timestep, self.number_of_timesteps,
                self.initial_temperature, self.initial_humidity,
                self.methodology, self.simulate_moisture,
                self.convergence_tolerance, self.relaxation_parameter,
                modeling_key)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, TransientCalculation) and \
            self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        return self.__class__(
            timestep=self._timestep,
            number_of_timesteps=self._number_of_timesteps,
            initial_temperature=self._initial_temperature,
            initial_humidity=self._initial_humidity,
            methodology=self._methodology,
            simulate_moisture=self._simulate_moisture,
            convergence_tolerance=self._convergence_tolerance,
            relaxation_parameter=self._relaxation_parameter,
            modeling_options=self.modeling_options)

    def __repr__(self):
        return 'TransientCalculation: {} steps x {} s [{}]'.format(
            self.number_of_timesteps, self.timestep, self.methodology)
