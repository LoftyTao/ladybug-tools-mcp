# coding=utf-8
"""Transient THERM boundary condition."""
from __future__ import division
import math
import os
import xml.etree.ElementTree as ET

from fairyfly._lockable import lockable
from fairyfly.typing import float_in_range, float_positive, \
    int_positive, uuid_from_therm_id

from ._base import _ThermConditionBase


@lockable
class Transient(_ThermConditionBase):
    """Transient or time-independent THERM 8 boundary condition type record.

    This object mirrors the THERM ``BoundaryConditionType`` record of
    ``TransientTypeBC.xml`` together with the per-timestep data of a
    ``timestep input files/<name>.xml`` member. Records with
    bc_type='SteadyState' carry constant values on the record itself.
    This writer always emits a timestep member for them as a single
    Index=1 step echoing those constants, while foreign archives may
    leave TimestepFileName empty or omitted on such records because the
    transient input reader accepts a SteadyState record without one.
    Records with bc_type='Transient' carry a timestep series for every
    family that the declared models consume, and the reader requires a
    TimestepFileName for them.

    Each entry of the timesteps dictionary is keyed by the 1-based timestep
    index and holds a dictionary of per-step values:

        * ``temperature`` -- environment temperature [C] (required by
          convection models).
        * ``humidity`` -- relative humidity [0,1] (required by all convection
          models and by ``use_humidity``).
        * ``film_coefficient`` -- [W/m2-K] (Fixed Convection Coefficient).
        * ``wind_speed`` -- [m/s] (ASHRAE/NFRC Outside, Yazdanian Klems,
          Kimura).
        * ``wind_direction`` -- [degrees] (Yazdanian Klems, Kimura).
        * ``radiation_temperature`` -- [C] (radiation timestep temperature).
        * ``hr`` -- fixed radiation coefficient [W/m2-K].
        * ``emissivity`` -- environment emissivity [0,1] (Black Body
          Radiation).
        * ``heat_flux`` -- [W/m2] (required when ``use_heat_flux``).
        * ``solar_radiation`` -- [W/m2] (required when a Solar record exists).
        * ``surface_temperature`` -- imposed surface temperature [C]
          (required when ``use_temperature``).

    Args:
        bc_type: 'Transient' for a timestep-driven condition or 'SteadyState'
            for a constant condition stored inside TransientTypeBC.xml.
            (Default: 'Transient').
        bc_model: 'Neumann' for convection-driven boundaries or 'Dirichlet'
            for imposed-value boundaries. (Default: 'Neumann').
        convection_model: Text for the convection model. Choose from
            'ASHRAE/NFRC Inside', 'ASHRAE/NFRC Outside',
            'Fixed Convection Coefficient', 'TARP', 'Yazdanian Klems',
            'Kimura'. 'Montazeri' exists in the schema but is rejected
            because the solver kernel has no implementation for it.
            Setting it to None omits the Convection record entirely.
            Model declarations are only meaningful on convection-driven
            records; records driven by use_heat_flux, use_temperature or
            a humidity-only Dirichlet pin (use_humidity without
            use_temperature) must pass None, since a declared but inert
            model would silently produce archives the transient input
            reader rejects. (Default: 'Fixed Convection Coefficient').
        radiation_model: Optional text for the radiation model. Choose from
            'Automatic Enclosure', 'Black Body Radiation',
            'Fixed Radiation Coefficient'. Like convection_model, it may only
            be declared on convection-driven records. (Default: None).
        timesteps: A dictionary of timestep dictionaries keyed by 1-based
            index (see above for the per-step keys), or a list of timestep
            dictionaries that will be numbered 1..N. Required for
            bc_type='Transient'. (Default: None).
        temperature: Constant environment temperature [C]; used for
            bc_type='SteadyState' records. (Default: None).
        film_coefficient: Constant film coefficient [W/m2-K]; used for
            bc_type='SteadyState' records. (Default: None).
        wind_speed: Constant wind speed [m/s] for SteadyState records.
            (Default: None).
        wind_direction: 'Windward' or 'Leeward'; used for SteadyState
            records. (Default: None).
        use_heat_flux: Boolean for whether the heat flux timesteps drive the
            boundary. (Default: False).
        heat_flux: Constant heat flux [W/m2] for SteadyState records.
            (Default: None).
        use_temperature: Boolean for whether imposed surface temperature
            timesteps drive the boundary. (Default: False).
        imposed_temperature: Constant imposed temperature [C] for SteadyState
            records. (Default: None).
        use_humidity: Boolean for whether humidity timesteps drive the
            moisture boundary. (Default: False).
        imposed_humidity: Constant humidity [0,1] for SteadyState records.
            (Default: None).
        radiation_temperature: Constant radiation temperature [C] for
            SteadyState records. (Default: None).
        surface_emissivity: Constant surface emissivity [0,1] for SteadyState
            records. (Default: None).
        view_factor: Constant view factor [0,1] for SteadyState records.
            (Default: None).
        hr: Constant radiation coefficient [W/m2-K] for SteadyState records
            with the 'Fixed Radiation Coefficient' model. (Default: None).
        solar_radiation: Constant solar radiation [W/m2] for SteadyState
            records. (Default: None).
        absorptance: Solar absorptance [0,1] that accompanies a Solar record.
            (Default: None).
        timestep_file_name: Name of the timestep input member inside the THMZ
            archive (without the 'timestep input files/' prefix). If None,
            'BC_TS_<identifier>.xml' is used. (Default: None).
        surface_tilt: Optional tilt angle in degrees for the surface geometry
            record. (Default: None).
        surface_length: Optional surface length in millimeters. If None, the
            writer uses the boundary segment length. (Default: None).
        building_width: Optional building width in meters for wind-driven
            convection models. (Default: None).
        building_height: Optional building height in meters. (Default: None).
        identifier: Text string for a unique object ID. Must be a UUID in the
            format xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx. If None, a UUID will
            automatically be generated. (Default: None).

    Properties:
        * identifier
        * display_name
        * bc_type
        * bc_model
        * convection_model
        * radiation_model
        * timesteps
        * use_heat_flux
        * use_temperature
        * use_humidity
        * timestep_file_name
        * color
        * protected
        * project_tag
        * user_data
    """
    __slots__ = (
        '_bc_type', '_bc_model', '_convection_model', '_radiation_model',
        '_timesteps', '_temperature', '_film_coefficient', '_wind_speed',
        '_wind_direction', '_use_heat_flux', '_heat_flux', '_use_temperature',
        '_imposed_temperature', '_use_humidity', '_imposed_humidity',
        '_radiation_temperature', '_surface_emissivity', '_view_factor',
        '_hr', '_solar_radiation', '_absorptance', '_timestep_file_name',
        '_surface_tilt', '_surface_length', '_building_width',
        '_building_height')
    BC_TYPES = ('Transient', 'SteadyState')
    BC_MODELS = ('Neumann', 'Dirichlet')
    CONVECTION_MODELS = (
        'ASHRAE/NFRC Outside', 'ASHRAE/NFRC Inside',
        'Fixed Convection Coefficient', 'TARP', 'Yazdanian Klems', 'Kimura')
    # Montazeri exists in the schema but the kernel has no BC implementation;
    # the contract lists it as declarable-but-rejected (THMZ-E5001).
    UNSUPPORTED_CONVECTION_MODELS = ('Montazeri',)
    RADIATION_MODELS = (
        'Automatic Enclosure', 'Black Body Radiation',
        'Fixed Radiation Coefficient')
    WIND_DIRECTIONS = ('Windward', 'Leeward')
    # XML record tag of each convection model inside ConvectionTimesteps
    # together with the extra per-step keys beyond temperature and humidity.
    CONVECTION_TIMESTEP_TAGS = {
        'ASHRAE/NFRC Inside': ('ASHRAETimestepInside', ()),
        'ASHRAE/NFRC Outside': ('ASHRAETimestepOutside', ('wind_speed',)),
        'Fixed Convection Coefficient':
            ('FixedConvectionFilmTimestep', ('film_coefficient',)),
        'TARP': ('TARPTimestep', ()),
        'Yazdanian Klems':
            ('YazdanianKlemsTimestep', ('wind_speed', 'wind_direction')),
        'Kimura': ('KimuraTimestep', ('wind_speed', 'wind_direction')),
        # parse/serialize-only; new objects may not declare Montazeri
        'Montazeri': ('MontazeriTimestep', ('wind_speed', 'wind_direction'))
    }
    RADIATION_TIMESTEP_TAGS = {
        'Fixed Radiation Coefficient':
            ('FixedRadiationCoefficientTimestep',
             ('radiation_temperature', 'hr')),
        'Black Body Radiation':
            ('BlackBodyRadiationTimestep',
             ('radiation_temperature', 'emissivity'))
    }
    TIMESTEP_FIELDS = (
        ('temperature', 'Temperature'),
        ('humidity', 'Humidity'),
        ('film_coefficient', 'FilmCoefficient'),
        ('wind_speed', 'WindSpeed'),
        ('wind_direction', 'WindDirection'),
        ('radiation_temperature', 'Temperature'),
        ('hr', 'hr'),
        ('emissivity', 'Emissivity'),
        ('heat_flux', 'HeatFlux'),
        ('solar_radiation', 'SolarRadiation'),
        ('surface_temperature', 'Temperature'))
    _TIMESTEP_KEYS = set(key for key, _ in TIMESTEP_FIELDS)
    # Field sets mirror the transient XSD and sequence reader. ProjectName
    # is a reader-supported extension and maps to the existing project_tag.
    TYPE_XML_FIELDS = {
        'BoundaryConditionType': (
            'UUID', 'Name', 'ProjectName', 'Protected', 'bcType', 'bcModel',
            'Convection', 'Radiation', 'Solar', 'UseHeatFlux', 'HeatFlux',
            'UseTemperature', 'Temperature', 'UseHumidity', 'Humidity', 'Color'),
        'Convection': ('Model', 'Temperature', 'FilmCoefficient', 'WindSpeed',
                       'WindDirection'),
        'Radiation': ('Model', 'Temperature', 'SurfaceEmissivity', 'ViewFactor', 'hr'),
        'Solar': ('SolarRadiation', 'Absorptance')
    }

    def __init__(
        self, bc_type='Transient', bc_model='Neumann',
        convection_model='Fixed Convection Coefficient', radiation_model=None,
        timesteps=None, temperature=None, film_coefficient=None,
        wind_speed=None, wind_direction=None,
        use_heat_flux=False, heat_flux=None, use_temperature=False,
        imposed_temperature=None, use_humidity=False, imposed_humidity=None,
        radiation_temperature=None, surface_emissivity=None, view_factor=None,
        hr=None, solar_radiation=None, absorptance=None,
        timestep_file_name=None, surface_tilt=None, surface_length=None,
        building_width=None, building_height=None, identifier=None
    ):
        """Initialize transient condition."""
        _ThermConditionBase.__init__(self, identifier)
        self.bc_type = bc_type
        self.bc_model = bc_model
        self.convection_model = convection_model
        self.radiation_model = radiation_model
        self.timesteps = timesteps
        self.temperature = temperature
        self.film_coefficient = film_coefficient
        self.wind_speed = wind_speed
        self.wind_direction = wind_direction
        self.use_heat_flux = use_heat_flux
        self.heat_flux = heat_flux
        self.use_temperature = use_temperature
        self.imposed_temperature = imposed_temperature
        self.use_humidity = use_humidity
        self.imposed_humidity = imposed_humidity
        self.radiation_temperature = radiation_temperature
        self.surface_emissivity = surface_emissivity
        self.view_factor = view_factor
        self.hr = hr
        self.solar_radiation = solar_radiation
        self.absorptance = absorptance
        self.timestep_file_name = timestep_file_name
        self.surface_tilt = surface_tilt
        self.surface_length = surface_length
        self.building_width = building_width
        self.building_height = building_height
        # cross-field consistency between the record and its timestep series
        if self._bc_type == 'SteadyState' and self._timesteps:
            raise ValueError(
                'A SteadyState Transient record cannot carry timesteps.')
        if self._bc_type == 'Transient' and not self._timesteps:
            raise ValueError(
                'A Transient condition requires a timestep series.')
        if self._bc_type == 'Transient' and self._timesteps:
            self._check_timesteps()
        if self._convection_driven() and self._convection_model is None:
            raise ValueError(
                'A convection-driven Transient record requires a '
                'convection_model; None is only valid for boundaries '
                'driven by use_heat_flux, use_temperature or a humidity '
                'pin.')
        if not self._convection_driven() and (
                self._convection_model is not None or
                self._radiation_model is not None):
            raise ValueError(
                'This Transient record does not drive convection; a '
                'declared convection_model or radiation_model would be '
                'inert metadata that the transient input reader still '
                'expects a timestep series for. Pass None for both.')

    @property
    def bc_type(self):
        """Get or set 'Transient' or 'SteadyState' for the condition record."""
        return self._bc_type

    @bc_type.setter
    def bc_type(self, value):
        if value is not None:
            for key in self.BC_TYPES:
                if key.lower() == str(value).lower():
                    value = key
                    break
            else:
                raise ValueError(
                    'Transient bc_type "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.BC_TYPES)))
            self._bc_type = value
        else:
            self._bc_type = 'Transient'

    @property
    def bc_model(self):
        """Get or set 'Neumann' or 'Dirichlet' for the condition model."""
        return self._bc_model

    @bc_model.setter
    def bc_model(self, value):
        if value is not None:
            for key in self.BC_MODELS:
                if key.lower() == str(value).lower():
                    value = key
                    break
            else:
                raise ValueError(
                    'Transient bc_model "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.BC_MODELS)))
            self._bc_model = value
        else:
            self._bc_model = 'Neumann'

    @property
    def convection_model(self):
        """Get or set the text for the convection model."""
        return self._convection_model

    @convection_model.setter
    def convection_model(self, value):
        if value is None:
            # None means the record carries no Convection block at all,
            # which is the THERM shape of a pure humidity pin (UseHumidity
            # on a Dirichlet record without UseTemperature).
            self._convection_model = None
            return
        clean_input = str(value)
        for key in self.UNSUPPORTED_CONVECTION_MODELS:
            if key.lower() == clean_input.lower():
                raise ValueError(
                    'THMZ-E5001: The "{}" convection model has no solver '
                    'implementation; the THMZ contract lists it as '
                    'declarable-but-rejected.'.format(key))
        for key in self.CONVECTION_MODELS:
            if key.lower() == clean_input.lower():
                value = key
                break
        else:
            raise ValueError(
                'Transient convection_model "{}" is not supported.\n'
                'Choose from the following:\n{}'.format(
                    value, '\n'.join(self.CONVECTION_MODELS)))
        self._convection_model = value

    @property
    def radiation_model(self):
        """Get or set the text for the radiation model or None."""
        return self._radiation_model

    @radiation_model.setter
    def radiation_model(self, value):
        if value is not None:
            clean_input = str(value)
            for key in self.RADIATION_MODELS:
                if key.lower() == clean_input.lower():
                    value = key
                    break
            else:
                raise ValueError(
                    'Transient radiation_model "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.RADIATION_MODELS)))
        self._radiation_model = value

    @property
    def timesteps(self):
        """Get or set the dictionary of timestep data keyed by 1-based index."""
        return self._timesteps

    @timesteps.setter
    def timesteps(self, value):
        if value is None:
            self._timesteps = None
            return
        if isinstance(value, (list, tuple)):  # numbered by position
            value = dict(enumerate(value, start=1))
        if not isinstance(value, dict):
            raise ValueError(
                'Expected a dictionary or list for timesteps. Got {}.'.format(
                    type(value)))
        series = {}
        for index, step in value.items():
            step_index = int_positive(index, 'timestep index')
            if not (step_index == index or index == str(step_index)):
                raise ValueError(
                    'Timestep index {} must be an integer.'.format(index))
            if step_index < 1:
                raise ValueError(
                    'Timestep index {} must be 1 or greater.'.format(index))
            if not isinstance(step, dict):
                raise ValueError(
                    'Timestep {} must be a dictionary. Got {}.'.format(
                        index, type(step)))
            unknown = set(step) - self._TIMESTEP_KEYS
            if unknown:
                raise ValueError(
                    'Timestep {} contains unknown keys: {}.'.format(
                        index, ', '.join(sorted(unknown))))
            for key, number in step.items():
                self._checked_step_value(
                    key, number, 'Transient "{}" Index={}/{}={!r}'.format(
                        self.display_name, step_index, key, number))
            series[step_index] = dict(step)
        self._timesteps = series

    @property
    def temperature(self):
        """Get or set the constant temperature of a SteadyState record [C]."""
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        if value is not None:
            value = float_in_range(
                value, mi=-273.15, input_name='condition temperature')
        self._temperature = value

    @property
    def film_coefficient(self):
        """Get or set the constant film coefficient of a SteadyState record."""
        return self._film_coefficient

    @film_coefficient.setter
    def film_coefficient(self, value):
        if value is not None:
            value = float_positive(value, 'film coefficient')
        self._film_coefficient = value

    @property
    def wind_speed(self):
        """Get or set the constant wind speed of a SteadyState record [m/s]."""
        return self._wind_speed

    @wind_speed.setter
    def wind_speed(self, value):
        if value is not None:
            value = float_positive(value, 'wind speed')
        self._wind_speed = value

    @property
    def wind_direction(self):
        """Get or set 'Windward' or 'Leeward' for a SteadyState record."""
        return self._wind_direction

    @wind_direction.setter
    def wind_direction(self, value):
        if value is not None:
            clean_input = str(value)
            for key in self.WIND_DIRECTIONS:
                if key.lower() == clean_input.lower():
                    value = key
                    break
            else:
                raise ValueError(
                    'Transient wind_direction "{}" is not supported.\n'
                    'Choose from the following:\n{}'.format(
                        value, '\n'.join(self.WIND_DIRECTIONS)))
        self._wind_direction = value

    @property
    def use_heat_flux(self):
        """Get or set whether heat flux timesteps drive the boundary."""
        return self._use_heat_flux

    @use_heat_flux.setter
    def use_heat_flux(self, value):
        self._use_heat_flux = bool(value)

    @property
    def heat_flux(self):
        """Get or set the constant heat flux of a SteadyState record [W/m2]."""
        return self._heat_flux

    @heat_flux.setter
    def heat_flux(self, value):
        if value is not None:
            value = float_in_range(value, input_name='condition heat flux')
        self._heat_flux = value

    @property
    def use_temperature(self):
        """Get or set whether temperature timesteps drive the boundary."""
        return self._use_temperature

    @use_temperature.setter
    def use_temperature(self, value):
        self._use_temperature = bool(value)

    @property
    def imposed_temperature(self):
        """Get or set the constant imposed temperature of a SteadyState record."""
        return self._imposed_temperature

    @imposed_temperature.setter
    def imposed_temperature(self, value):
        if value is not None:
            value = float_in_range(
                value, mi=-273.15, input_name='imposed temperature')
        self._imposed_temperature = value

    @property
    def use_humidity(self):
        """Get or set whether humidity timesteps drive the boundary."""
        return self._use_humidity

    @use_humidity.setter
    def use_humidity(self, value):
        self._use_humidity = bool(value)

    @property
    def imposed_humidity(self):
        """Get or set the constant humidity of a SteadyState record [0,1]."""
        return self._imposed_humidity

    @imposed_humidity.setter
    def imposed_humidity(self, value):
        if value is not None:
            value = float_in_range(value, 0.0, 1.0, 'imposed humidity')
        self._imposed_humidity = value

    @property
    def radiation_temperature(self):
        """Get or set the constant radiation temperature of a SteadyState record."""
        return self._radiation_temperature

    @radiation_temperature.setter
    def radiation_temperature(self, value):
        if value is not None:
            value = float_in_range(
                value, mi=-273.15, input_name='radiation temperature')
        self._radiation_temperature = value

    @property
    def surface_emissivity(self):
        """Get or set the constant surface emissivity of a SteadyState record."""
        return self._surface_emissivity

    @surface_emissivity.setter
    def surface_emissivity(self, value):
        if value is not None:
            value = float_in_range(value, 0.0, 1.0, 'surface emissivity')
        self._surface_emissivity = value

    @property
    def view_factor(self):
        """Get or set the constant view factor of a SteadyState record."""
        return self._view_factor

    @view_factor.setter
    def view_factor(self, value):
        if value is not None:
            value = float_in_range(value, 0.0, 1.0, 'view factor')
        self._view_factor = value

    @property
    def hr(self):
        """Get or set the constant radiation coefficient of a SteadyState record."""
        return self._hr

    @hr.setter
    def hr(self, value):
        if value is not None:
            value = float_positive(value, 'radiation coefficient')
        self._hr = value

    @property
    def solar_radiation(self):
        """Get or set the constant solar radiation of a SteadyState record."""
        return self._solar_radiation

    @solar_radiation.setter
    def solar_radiation(self, value):
        if value is not None:
            value = float_positive(value, 'solar radiation')
        self._solar_radiation = value

    @property
    def absorptance(self):
        """Get or set the solar absorptance of a Solar record."""
        return self._absorptance

    @absorptance.setter
    def absorptance(self, value):
        if value is not None:
            value = float_in_range(value, 0.0, 1.0, 'solar absorptance')
        self._absorptance = value

    @property
    def timestep_file_name(self):
        """Get or set the timestep member name inside 'timestep input files/'."""
        if self._timestep_file_name is None:
            return 'BC_TS_{}.xml'.format(self.identifier)
        return self._timestep_file_name

    @timestep_file_name.setter
    def timestep_file_name(self, value):
        if value is not None:
            value = str(value)
            if not value.lower().endswith('.xml'):
                raise ValueError(
                    'timestep_file_name must end with .xml. '
                    'Got {}.'.format(value))
            if os.path.basename(value) != value or '/' in value \
                    or '\\' in value:
                raise ValueError(
                    'timestep_file_name must be a bare file name without '
                    'directories. Got {}.'.format(value))
        self._timestep_file_name = value

    @property
    def surface_tilt(self):
        """Get or set the surface tilt angle in degrees."""
        return self._surface_tilt

    @surface_tilt.setter
    def surface_tilt(self, value):
        if value is not None:
            value = float_in_range(value, 0.0, 360.0, 'surface tilt')
        self._surface_tilt = value

    @property
    def surface_length(self):
        """Get or set the surface length in millimeters."""
        return self._surface_length

    @surface_length.setter
    def surface_length(self, value):
        if value is not None:
            value = float_positive(value, 'surface length')
        self._surface_length = value

    @property
    def building_width(self):
        """Get or set the building width in meters."""
        return self._building_width

    @building_width.setter
    def building_width(self, value):
        if value is not None:
            value = float_positive(value, 'building width')
        self._building_width = value

    @property
    def building_height(self):
        """Get or set the building height in meters."""
        return self._building_height

    @building_height.setter
    def building_height(self, value):
        if value is not None:
            value = float_positive(value, 'building height')
        self._building_height = value

    def _is_humidity_pin(self):
        """Whether the record is a humidity-only Dirichlet pin.

        Such a pin (UseHumidity on a Dirichlet record without
        UseTemperature) is driven solely by its HumidityTimestep series;
        pin semantics dominate over any declared Convection block, which
        the solver treats as inert metadata (contract section 5).
        """
        return self._use_humidity and self._bc_model == 'Dirichlet' \
            and not self._use_temperature

    def _convection_driven(self):
        """Whether the record drives convection/radiation timestep series."""
        return not self._use_heat_flux and not self._use_temperature \
            and not self._is_humidity_pin()

    def _required_step_keys(self):
        """The per-step keys the declared models consume."""
        keys = []
        if self._convection_driven():
            if self._convection_model is not None:
                keys.append('temperature')
                keys.append('humidity')
                keys.extend(
                    self.CONVECTION_TIMESTEP_TAGS[self._convection_model][1])
            if self._radiation_model in self.RADIATION_TIMESTEP_TAGS:
                keys.extend(self.RADIATION_TIMESTEP_TAGS[
                    self._radiation_model][1])
        if self._use_heat_flux:
            keys.append('heat_flux')
        if self._solar_radiation is not None or self._absorptance is not None:
            keys.append('solar_radiation')
        if self._use_temperature:
            keys.append('surface_temperature')
        if self._use_humidity:
            keys.append('humidity')
        return keys

    def _check_timesteps(self):
        """Check that every timestep carries the values the models need."""
        required = self._required_step_keys()
        for index in sorted(self._timesteps):
            step = self._timesteps[index]
            missing = [key for key in required if key not in step]
            if missing:
                raise ValueError(
                    'Timestep {} is missing values for: {}.'.format(
                        index, ', '.join(missing)))
            for key, value in step.items():
                self._checked_step_value(
                    key, value, 'Transient "{}" Index={}/{}={!r}'.format(
                        self.display_name, index, key, value))

    def _ordered_steps(self):
        """Timesteps as (index, step) pairs sorted by index."""
        return sorted(self._timesteps.items())

    @staticmethod
    def _step_value(step, key):
        return step[key]

    def _timestep_element(self, parent, tag, index, step, fields):
        """Append a timestep record element to a parent element."""
        record = ET.SubElement(parent, tag)
        xml_index = ET.SubElement(record, 'Index')
        xml_index.text = str(index)
        for key in fields:
            self._checked_step_value(
                key, step[key], 'Transient "{}" {}/Index={}/{}={!r}'.format(
                    self.display_name, tag, index, key, step[key]))
            xml_value = ET.SubElement(record, dict(self.TIMESTEP_FIELDS)[key])
            xml_value.text = str(step[key])
        return record

    # record constants that map onto the per-step keys of a timestep file
    # for bcType='SteadyState' records
    _STEADY_CONSTANTS = {
        'temperature': '_temperature',
        'film_coefficient': '_film_coefficient',
        'wind_speed': '_wind_speed',
        'wind_direction': '_wind_direction',
        'radiation_temperature': '_radiation_temperature',
        'hr': '_hr',
        'emissivity': '_surface_emissivity',
        'heat_flux': '_heat_flux',
        'solar_radiation': '_solar_radiation',
        'surface_temperature': '_imposed_temperature',
        'humidity': '_imposed_humidity'}

    def _steady_step(self):
        """One constant timestep dictionary echoing the record constants.

        SteadyState records carry constant values on the record itself and
        the solver reads only those constants; this writer still emits the
        referenced timestep member as a single Index=1 step holding the
        declared constants, even though the transient input reader also
        accepts foreign SteadyState records that carry no file name. A
        use_humidity record without an imposed_humidity constant is
        rejected instead of writing an invented value.
        """
        keys = []
        if self._convection_model is not None:
            conv_keys = ('temperature', 'humidity') + \
                self.CONVECTION_TIMESTEP_TAGS[self._convection_model][1]
            if self._convection_driven() or all(
                    getattr(self, self._STEADY_CONSTANTS[key]) is not None
                    for key in conv_keys if key != 'humidity'):
                keys.extend(conv_keys)
        if self._radiation_model in self.RADIATION_TIMESTEP_TAGS:
            rad_keys = self.RADIATION_TIMESTEP_TAGS[self._radiation_model][1]
            if self._convection_driven() or all(
                    getattr(self, self._STEADY_CONSTANTS[key]) is not None
                    for key in rad_keys):
                keys.extend(rad_keys)
        if self._use_heat_flux:
            keys.append('heat_flux')
        if self._solar_radiation is not None:
            keys.append('solar_radiation')
        if self._use_temperature:
            keys.append('surface_temperature')
        if self._use_humidity:
            keys.append('humidity')
        step = {}
        for key in dict.fromkeys(keys):
            value = getattr(self, self._STEADY_CONSTANTS[key])
            if value is None and key == 'humidity' \
                    and not self._use_humidity:
                # Convection timestep entries carry a required Humidity
                # column; when the record makes no humidity statement the
                # inert 0 is written because the solver reads only the
                # record constants for this member. A use_humidity pin
                # instead requires its real imposed_humidity.
                value = 0.0
            if value is None:
                raise ValueError(
                    'A SteadyState record driving {} requires the {} '
                    'constant.'.format(
                        self.display_name,
                        self._STEADY_CONSTANTS[key].lstrip('_')))
            step[key] = value
        return step

    def to_steady_timestep_xml(self):
        """Get the timestep member of a bcType='SteadyState' record.

        Returns:
            An XML Element mirroring a ``timestep input files/<name>.xml``
            member that holds a single constant step for each family the
            record declares.

        Raises:
            ValueError: The record is not bc_type='SteadyState', or a
                declared driving family lacks its record constant (a
                use_humidity pin without imposed_humidity is an error, not
                an inert zero).
        """
        if self._bc_type != 'SteadyState':
            raise ValueError(
                'Only SteadyState records use to_steady_timestep_xml.')
        return self._timestep_xml(((1, self._steady_step()),))

    def to_timestep_xml(self):
        """Get a THERM InputBoundaryConditionsData element for the timesteps.

        Returns:
            An XML Element mirroring a ``timestep input files/<name>.xml``
            member.

        Raises:
            ValueError: The record is not bc_type='Transient' or it lacks
                a timestep series, required values are missing or invalid,
                or supplied values have no serialized driving family.
        """
        if self._bc_type != 'Transient':
            raise ValueError(
                'Only Transient records carry timestep input files.')
        if not self._timesteps:
            raise ValueError('A Transient condition requires timesteps.')
        self._check_timesteps()
        return self._timestep_xml(self._ordered_steps())

    def _timestep_xml(self, ordered_steps):
        """Serialize ordered (index, step) pairs as a timestep member."""
        serialized_keys = set()
        xml_root = ET.Element('InputBoundaryConditionsData')
        xml_ver = ET.SubElement(xml_root, 'Version')
        xml_ver.text = '1'
        xml_name = ET.SubElement(xml_root, 'Name')
        xml_name.text = self.display_name
        xml_bct = ET.SubElement(xml_root, 'BoundaryConditionTransient')
        # THERM writes the convection and radiation series only when they
        # drive the boundary; UseHeatFlux/UseTemperature records and
        # humidity pins omit them. A foreign record that still declares a
        # model on a non-driven boundary keeps its series only when every
        # step carries the family fields; otherwise the family is skipped
        # and the written record stays faithful to the pin semantics.
        if self._convection_model in self.CONVECTION_TIMESTEP_TAGS:
            tag, extras = self.CONVECTION_TIMESTEP_TAGS[self._convection_model]
            fields = ('temperature', 'humidity') + extras
            if self._convection_driven() or all(
                    all(key in step for key in fields)
                    for _, step in ordered_steps):
                xml_conv = ET.SubElement(xml_bct, 'ConvectionTimesteps')
                serialized_keys.update(fields)
                for index, step in ordered_steps:
                    self._timestep_element(xml_conv, tag, index, step, fields)
        if self._radiation_model in self.RADIATION_TIMESTEP_TAGS:
            tag, fields = self.RADIATION_TIMESTEP_TAGS[self._radiation_model]
            if self._convection_driven() or all(
                    all(key in step for key in fields)
                    for _, step in ordered_steps):
                xml_rad = ET.SubElement(xml_bct, 'RadiationTimesteps')
                serialized_keys.update(fields)
                for index, step in ordered_steps:
                    self._timestep_element(xml_rad, tag, index, step, fields)
        has_solar = self._solar_radiation is not None or \
            self._absorptance is not None or \
            any('solar_radiation' in step for _, step in ordered_steps)
        for flag, key, tag in (
                (self._use_heat_flux, 'heat_flux', 'HeatFluxTimestep'),
                (has_solar, 'solar_radiation', 'SolarRadiationTimestep'),
                (self._use_temperature, 'surface_temperature',
                 'TemperatureTimestep'),
                (self._use_humidity, 'humidity', 'HumidityTimestep')):
            if not flag:
                continue
            serialized_keys.add(key)
            for index, step in ordered_steps:
                self._timestep_element(xml_bct, tag, index, step, (key,))
        for index, step in ordered_steps:
            omitted = dict((key, value) for key, value in step.items()
                           if key not in serialized_keys)
            if omitted:
                raise ValueError('THMZ-E2005: Transient "{}" Index={} has '
                                 'values without a serialized family: {!r}; '
                                 'this object cannot preserve them.'.format(
                                     self.display_name, index, omitted))
        return xml_root

    def to_timestep_xml_str(self):
        """Get a THERM XML string for the timestep input member."""
        xml_root = self.to_timestep_xml()
        try:  # try to indent the XML to make it read-able
            ET.indent(xml_root)
            return ET.tostring(xml_root, encoding='unicode')
        except AttributeError:  # we are in Python 2 and no indent is available
            return ET.tostring(xml_root)

    def to_transient_data_xml(self, boundary_element, segment_length):
        """Write the Boundary/TransientData block of a THERM Model Boundary.

        Args:
            boundary_element: The Boundary XML element to which the generated
                TransientData element will be added.
            segment_length: The length of the boundary segment in millimeters;
                used for Surface/Length when surface_length is not set.
        """
        xml_td = ET.SubElement(boundary_element, 'TransientData')
        xml_uuid = ET.SubElement(xml_td, 'UUID')
        xml_uuid.text = self.identifier
        xml_file = ET.SubElement(xml_td, 'TimestepFileName')
        # SteadyState records reference the constant-step member written by
        # to_steady_timestep_xml. This writer always emits the member even
        # though the solver only reads the record constants and the reader
        # tolerates a foreign SteadyState record without a file name.
        xml_file.text = self.timestep_file_name
        if self._surface_tilt is not None or self._surface_length is not None \
                or segment_length is not None:
            xml_surface = ET.SubElement(xml_td, 'Surface')
            xml_tilt = ET.SubElement(xml_surface, 'Tilt')
            xml_tilt.text = '90' if self._surface_tilt is None \
                else str(self._surface_tilt)
            xml_len = ET.SubElement(xml_surface, 'Length')
            xml_len.text = str(
                self._surface_length if self._surface_length is not None
                else segment_length)
        if self._building_width is not None or self._building_height is not None:
            xml_building = ET.SubElement(xml_td, 'Building')
            xml_width = ET.SubElement(xml_building, 'Width')
            xml_width.text = '0' if self._building_width is None \
                else str(self._building_width)
            xml_height = ET.SubElement(xml_building, 'Height')
            xml_height.text = '0' if self._building_height is None \
                else str(self._building_height)
        return xml_td

    @classmethod
    def from_therm_xml(cls, xml_element, timesteps=None):
        """Create a Transient condition from a BoundaryConditionType element.

        Args:
            xml_element: An XML element of a THERM BoundaryConditionType record.
            timesteps: An optional dictionary or list of timestep dictionaries
                to attach when the record's bcType is 'Transient'.

        Raises:
            ValueError: Unknown fields or attributes, duplicate single-valued
                fields, missing required fields, invalid values, or unsupported
                models carry the corresponding THMZ-E contract code.
        """
        context = 'Transient "{}"'.format(
            xml_element.findtext('Name') or '<unnamed>')
        if xml_element.tag != 'BoundaryConditionType':
            raise ValueError('THMZ-E2000: {} expected BoundaryConditionType; '
                             'got {}.'.format(context, xml_element.tag))
        cls._validate_xml_tree(xml_element, cls.TYPE_XML_FIELDS, context)
        for tag in ('UUID', 'Name', 'Protected', 'bcType', 'bcModel',
                    'UseHeatFlux', 'UseTemperature', 'UseHumidity', 'Color'):
            cls._required_xml_text(xml_element, tag, context)
        for tag in ('Protected', 'UseHeatFlux', 'UseTemperature', 'UseHumidity'):
            if xml_element.findtext(tag) not in ('true', 'false'):
                raise ValueError('THMZ-E2005: {} BoundaryConditionType/{}={!r} '
                                 'must be true or false.'.format(
                                     context, tag, xml_element.findtext(tag)))
        for tag in ('Convection', 'Radiation'):
            block = xml_element.find(tag)
            if block is not None:
                cls._required_xml_text(block, 'Model', context + '/' + tag)
        # create the base condition from the UUID and type fields
        xml_uuid = xml_element.find('UUID')
        identifier = xml_uuid.text
        if len(identifier) == 31:
            identifier = uuid_from_therm_id(identifier)
        xml_conv_model = xml_element.findtext('Convection/Model')
        xml_rad_model = xml_element.findtext('Radiation/Model')
        driven = not (xml_element.findtext('UseHeatFlux') == 'true' or
                      xml_element.findtext('UseTemperature') == 'true' or
                      (xml_element.findtext('UseHumidity') == 'true' and
                       xml_element.findtext('bcModel') == 'Dirichlet'))
        # records that do not drive convection may still carry the default
        # Convection or Radiation block as inert metadata in THERM-produced
        # archives; the constructor rejects new mixed declarations, so they
        # are restored verbatim after construction to keep parsing lossless
        cond = cls(
            bc_type=xml_element.findtext('bcType'),
            bc_model=xml_element.findtext('bcModel'),
            convection_model=xml_conv_model if driven else None,
            radiation_model=xml_rad_model if driven else None,
            timesteps=timesteps or _placeholder_timesteps(
                xml_element.findtext('bcType')),
            use_heat_flux=xml_element.findtext('UseHeatFlux') == 'true',
            use_temperature=xml_element.findtext('UseTemperature') == 'true',
            use_humidity=xml_element.findtext('UseHumidity') == 'true',
            solar_radiation=xml_element.findtext('Solar/SolarRadiation'),
            absorptance=xml_element.findtext('Solar/Absorptance'),
            identifier=identifier)
        if not driven:
            # Preserve valid inert declarations without bypassing model-level
            # rejection (notably Montazeri) or enum validation.
            cond.convection_model = xml_conv_model
            cond.radiation_model = xml_rad_model
        # the constructor raises on Transient records without timesteps; when
        # timesteps was None a placeholder was passed so it can be replaced.
        if timesteps is None and cond._bc_type == 'Transient':
            cond._timesteps = None
        # assign the convection record constants
        xml_conv = xml_element.find('Convection')
        if xml_conv is not None:
            cond.temperature = xml_conv.findtext('Temperature')
            cond.film_coefficient = xml_conv.findtext('FilmCoefficient')
            cond.wind_speed = xml_conv.findtext('WindSpeed')
            cond.wind_direction = xml_conv.findtext('WindDirection')
        # assign the radiation record constants
        xml_rad = xml_element.find('Radiation')
        if xml_rad is not None:
            cond.radiation_temperature = xml_rad.findtext('Temperature')
            cond.surface_emissivity = xml_rad.findtext('SurfaceEmissivity')
            cond.view_factor = xml_rad.findtext('ViewFactor')
            cond.hr = xml_rad.findtext('hr')
        # assign the remaining constant values (flags are set in the ctor)
        cond.heat_flux = xml_element.findtext('HeatFlux')
        cond.imposed_temperature = xml_element.findtext('Temperature')
        cond.imposed_humidity = xml_element.findtext('Humidity')
        # assign the name and color if they are specified
        xml_name = xml_element.find('Name')
        if xml_name is not None:
            cond.display_name = xml_name.text
        cond.project_tag = xml_element.findtext('ProjectName')
        xml_col = xml_element.find('Color')
        if xml_col is not None:
            cond.color = xml_col.text
        xml_protect = xml_element.find('Protected')
        if xml_protect is not None:
            cond.protected = True if xml_protect.text == 'true' else False
        return cond

    @classmethod
    def from_therm_xml_str(cls, xml_str, timesteps=None):
        """Create a Transient condition from an XML text string.

        Args:
            xml_str: An XML text string of a THERM BoundaryConditionType record.
            timesteps: An optional dictionary or list of timestep dictionaries.
        """
        root = ET.fromstring(xml_str)
        if root.tag == 'BoundaryConditionType':
            return cls.from_therm_xml(root, timesteps)
        # allow passing a whole BoundaryConditionsType document
        record = root.find('BoundaryConditionType')
        if record is None:
            raise ValueError('Expected a BoundaryConditionType element.')
        return cls.from_therm_xml(record, timesteps)

    @classmethod
    def timesteps_from_xml(cls, xml_element):
        """Create a timestep dictionary from an InputBoundaryConditionsData element.

        Args:
            xml_element: An XML element of a THERM InputBoundaryConditionsData
                record (the content of a ``timestep input files/*.xml`` member).

        Returns:
            A dictionary of timestep dictionaries keyed by 1-based index.

        Raises:
            ValueError: Unknown or duplicate single-valued XML content, or a
                valid input sequence this index-keyed object cannot preserve.
                Restarted indices within one family are legal for sequence
                readers but cannot be represented here (THMZ-E2005).
                Cross-family shared indices remain valid when values agree.
                Independent family periods, schema-location metadata and a
                container Index likewise require storage this object lacks;
                they are explicitly rejected rather than discarded or padded.
        """
        context = 'Transient timesteps "{}"'.format(
            xml_element.findtext('Name') or '<unnamed>')
        if xml_element.tag not in ('InputBoundaryConditionsData',
                                   'BoundaryConditionTransient'):
            raise ValueError('THMZ-E2000: {} unexpected root {}.'.format(
                context, xml_element.tag))
        conv_fields = dict((tag, ('temperature', 'humidity') + extras)
                           for tag, extras in cls.CONVECTION_TIMESTEP_TAGS.values())
        rad_fields = dict(cls.RADIATION_TIMESTEP_TAGS.values())
        # This spelling is emitted by one upstream serializer and is accepted
        # as an alias by the reader; it has the same modeled fields.
        rad_fields['FixedRadiationTimestep'] = rad_fields[
            'FixedRadiationCoefficientTimestep']
        scalar_fields = {'HeatFluxTimestep': ('heat_flux',),
                         'SolarRadiationTimestep': ('solar_radiation',),
                         'TemperatureTimestep': ('surface_temperature',),
                         'HumidityTimestep': ('humidity',)}
        fields_by_tag = dict(conv_fields)
        fields_by_tag.update(rad_fields)
        fields_by_tag.update(scalar_fields)
        grammar = {
            'InputBoundaryConditionsData': ('Version', 'Name', 'BoundaryConditionTransient'),
            'BoundaryConditionTransient': ('Index', 'ConvectionTimesteps',
                                          'RadiationTimesteps') + tuple(scalar_fields),
            'ConvectionTimesteps': tuple(conv_fields),
            'RadiationTimesteps': tuple(rad_fields)}
        tag_for_key = dict(cls.TIMESTEP_FIELDS)
        for tag, fields in fields_by_tag.items():
            grammar[tag] = ('Index',) + tuple(tag_for_key[key] for key in fields)
        cls._validate_xml_tree(xml_element, grammar, context,
                               repeatable=set(fields_by_tag))
        if xml_element.tag == 'InputBoundaryConditionsData':
            cls._required_xml_text(xml_element, 'Name', context)
            version = xml_element.find('Version')
            if version is not None and version.text != '1':
                raise ValueError('THMZ-E2000: {} Version={!r}; expected 1.'.format(
                    context, version.text))
        if xml_element.tag == 'BoundaryConditionTransient':
            xml_bct = xml_element
        else:
            xml_bct = xml_element.find('BoundaryConditionTransient')
        timesteps = {}
        if xml_bct is None:
            return timesteps
        if xml_bct.find('Index') is not None:
            raise ValueError('THMZ-E2005: {} BoundaryConditionTransient/Index={!r}: '
                             'this timestep dictionary cannot preserve the '
                             'container index.'.format(context, xml_bct.findtext('Index')))
        seen_indices = {}

        def step_index(record, position):
            element = record.find('Index')
            if element is None:
                return position
            text = element.text
            try:
                index = int(text)
            except (TypeError, ValueError, OverflowError):
                raise ValueError('THMZ-E2004: {} {}/Index={!r} must be an '
                                 'integer.'.format(context, record.tag, text))
            if index < 1:
                raise ValueError('THMZ-E2004: {} {}/Index={!r} must be >= 1.'.format(
                    context, record.tag, text))
            return index

        def put(record, position, fields):
            index = step_index(record, position)
            family = 'FixedRadiationCoefficientTimestep' \
                if record.tag == 'FixedRadiationTimestep' else record.tag
            indices = seen_indices.setdefault(family, set())
            if index in indices:
                raise ValueError('THMZ-E2005: {} {} Index={}: this index-keyed '
                                 'timestep dictionary cannot preserve repeated '
                                 'records or restarted sequences; values={!r}.'.format(
                                     context, record.tag, index,
                                     ET.tostring(record, encoding='utf-8')))
            indices.add(index)
            step = timesteps.setdefault(index, {})
            for key in fields:
                tag = dict(cls.TIMESTEP_FIELDS)[key]
                text = cls._required_xml_text(record, tag, context)
                try:
                    value = float(text)
                except (TypeError, ValueError, OverflowError):
                    raise ValueError('THMZ-E2004: {} {}/{}={!r} must be numeric.'.format(
                        context, record.tag, tag, text))
                value = cls._checked_step_value(
                    key, value, '{} {}/{}={!r}'.format(context, record.tag, tag, text))
                if key in step and step[key] != value:
                    raise ValueError('THMZ-E2005: {} {} Index={}/{}={!r} conflicts '
                                     'with {!r}; this object cannot preserve both '
                                     'values.'.format(context, record.tag, index,
                                                     tag, value, step[key]))
                step[key] = value
            return index

        for group_tag in ('ConvectionTimesteps', 'RadiationTimesteps'):
            group = xml_bct.find(group_tag)
            if group is None:
                continue
            families = set('FixedRadiationCoefficientTimestep'
                           if r.tag == 'FixedRadiationTimestep' else r.tag for r in group)
            if len(families) > 1:
                raise ValueError('THMZ-E2005: {} {}={!r}: this object cannot '
                                 'preserve multiple model families.'.format(
                                     context, group_tag, sorted(families)))
            for position, record in enumerate(group, 1):
                put(record, position, fields_by_tag[record.tag])
        for tag, key in (('HeatFluxTimestep', 'heat_flux'),
                         ('SolarRadiationTimestep', 'solar_radiation'),
                         ('TemperatureTimestep', 'surface_temperature'),
                         ('HumidityTimestep', 'humidity')):
            for position, record in enumerate(xml_bct.findall(tag), 1):
                put(record, position, (key,))
        # The public object has one index-keyed dictionary, not independent
        # sequence storage per family. Different family periods would be
        # padded on export and change the original boundary input.
        all_indices = set(timesteps)
        for family, indices in seen_indices.items():
            if indices != all_indices:
                raise ValueError('THMZ-E2005: {} {} indices={!r}: this object '
                                 'cannot preserve independent family periods '
                                 'against combined indices={!r}.'.format(
                                     context, family, sorted(indices), sorted(all_indices)))
        return timesteps

    @staticmethod
    def _required_xml_text(element, tag, context):
        """Read one modeled required leaf after structural validation."""
        text = element.findtext(tag)
        if text is None or not text.strip():
            raise ValueError('THMZ-E2003: {} {}/{} is required.'.format(
                context, element.tag, tag))
        return text

    @staticmethod
    def _checked_step_value(key, value, context):
        """Validate modeled finite numbers and physical ranges."""
        if isinstance(value, bool):
            raise ValueError('THMZ-E2004: {} must be numeric, not boolean.'.format(context))
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            raise ValueError('THMZ-E2004: {} must be numeric.'.format(context))
        invalid = math.isnan(number) or math.isinf(number)
        if key in ('humidity', 'emissivity'):
            invalid = invalid or not 0 <= number <= 1
        elif key in ('temperature', 'radiation_temperature', 'surface_temperature'):
            invalid = invalid or number < -273.15
        elif key in ('film_coefficient', 'hr', 'wind_speed', 'solar_radiation'):
            invalid = invalid or number < 0
        if invalid:
            raise ValueError('THMZ-E2004: {} is outside its finite physical '
                             'domain.'.format(context))
        return number

    @classmethod
    def _validate_xml_tree(cls, element, grammar, context, repeatable=(), path=None):
        """Reject XML content that targeted field extraction would otherwise lose."""
        path = element.tag if path is None else path
        if element.attrib:
            raise ValueError('THMZ-E2001: {} {}/attributes={!r}: this object '
                             'cannot preserve attributes.'.format(
                                 context, path, element.attrib))
        allowed = grammar.get(element.tag, ())
        if allowed and element.text and element.text.strip():
            raise ValueError('THMZ-E2001: {} {}/text={!r} cannot be preserved.'.format(
                context, path, element.text))
        seen = set()
        for child in element:
            child_path = path + '/' + child.tag
            if child.tag not in allowed:
                raise ValueError('THMZ-E2001: {} unknown {}={!r}.'.format(
                    context, child_path, ET.tostring(child, encoding='utf-8')))
            if child.tag in seen and child.tag not in repeatable:
                raise ValueError('THMZ-E2002: {} duplicate {}={!r}.'.format(
                    context, child_path, ET.tostring(child, encoding='utf-8')))
            seen.add(child.tag)
            cls._validate_xml_tree(child, grammar, context, repeatable, child_path)
            if child.tail and child.tail.strip():
                raise ValueError('THMZ-E2001: {} {}/tail={!r} cannot be preserved.'.format(
                    context, child_path, child.tail))

    @classmethod
    def timesteps_from_xml_str(cls, xml_str):
        """Create a timestep dictionary from an XML text string."""
        return cls.timesteps_from_xml(ET.fromstring(xml_str))

    @classmethod
    def from_dict(cls, data):
        """Create a Transient condition from a dictionary.

        Args:
            data: A python dictionary in the following format

        .. code-block:: python

            {
            "type": 'Transient',
            "identifier": 'f26f3597-e3ee-43fe-a0b3-ec673f993d86',
            "display_name": 'ORNL Exterior',
            "bc_type": 'Transient',
            "bc_model": 'Neumann',
            "convection_model": 'Fixed Convection Coefficient',
            "radiation_model": 'Black Body Radiation',
            "timesteps": {'1': {'temperature': 10, 'humidity': 0.1,
                'film_coefficient': 7, 'radiation_temperature': 10,
                'emissivity': 0.9}},
            "use_heat_flux": False,
            "use_temperature": False,
            "use_humidity": False
            }
        """
        if data['type'] != 'Transient':
            raise ValueError(
                'Expected Transient. Got {}.'.format(data['type']))

        scalar_args = (
            'temperature', 'film_coefficient', 'wind_speed', 'wind_direction',
            'heat_flux', 'imposed_temperature', 'imposed_humidity',
            'radiation_temperature', 'surface_emissivity', 'view_factor', 'hr',
            'solar_radiation', 'absorptance', 'timestep_file_name',
            'surface_tilt', 'surface_length', 'building_width',
            'building_height')
        kwargs = {'identifier': data.get('identifier')}
        for key in ('bc_type', 'bc_model', 'convection_model',
                    'radiation_model', 'timesteps', 'use_heat_flux',
                    'use_temperature', 'use_humidity'):
            if key in data:
                kwargs[key] = data[key]
        for key in scalar_args:
            if key in data and data[key] is not None:
                kwargs[key] = data[key]
        # the constructor rejects model declarations on records that do not
        # drive convection; dictionaries parsed from foreign records may
        # legitimately carry them, so they are restored after construction
        driven = not (kwargs.get('use_heat_flux', False) or
                      kwargs.get('use_temperature', False) or
                      (kwargs.get('use_humidity', False) and
                       str(kwargs.get('bc_model', 'Neumann')).lower() ==
                       'dirichlet'))
        if not driven:
            kwargs['convection_model'] = None
            kwargs['radiation_model'] = None
        new_cond = cls(**kwargs)
        if not driven:
            new_cond.convection_model = data.get('convection_model')
            new_cond.radiation_model = data.get('radiation_model')
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
        """Get an THERM XML BoundaryConditionType element of the condition.

        Args:
            bcs_element: An optional XML Element for the BoundaryConditionsType
                to which the generated objects will be added. If None, a new
                XML Element will be generated.

        .. code-block:: xml

            <BoundaryConditionType>
                <UUID>1810f37a-de4d-4e2d-95d5-09fe01157c34</UUID>
                <Name>ORNL Exterior</Name>
                <Protected>false</Protected>
                <bcType>Transient</bcType>
                <bcModel>Neumann</bcModel>
                <Convection>
                    <Model>Fixed Convection Coefficient</Model>
                </Convection>
                <UseHeatFlux>false</UseHeatFlux>
                <UseTemperature>false</UseTemperature>
                <UseHumidity>false</UseHumidity>
                <Color>0x0080C0</Color>
            </BoundaryConditionType>
        """
        # create a new BoundaryConditionsType element if one is not specified
        if bcs_element is not None:
            xml_cond = ET.SubElement(bcs_element, 'BoundaryConditionType')
        else:
            xml_cond = ET.Element('BoundaryConditionType')
        # add all of the required basic attributes
        xml_id = ET.SubElement(xml_cond, 'UUID')
        xml_id.text = self.identifier
        xml_name = ET.SubElement(xml_cond, 'Name')
        xml_name.text = self.display_name
        if self._project_tag is not None:
            ET.SubElement(xml_cond, 'ProjectName').text = self.project_tag
        xml_protect = ET.SubElement(xml_cond, 'Protected')
        xml_protect.text = 'true' if self.protected else 'false'
        xml_bct = ET.SubElement(xml_cond, 'bcType')
        xml_bct.text = self.bc_type
        xml_bcm = ET.SubElement(xml_cond, 'bcModel')
        xml_bcm.text = self.bc_model
        # write the convection record with its SteadyState constants
        if self._convection_model is not None:
            xml_conv = ET.SubElement(xml_cond, 'Convection')
            xml_model = ET.SubElement(xml_conv, 'Model')
            xml_model.text = self.convection_model
            for value, tag in ((self._temperature, 'Temperature'),
                               (self._film_coefficient, 'FilmCoefficient'),
                               (self._wind_speed, 'WindSpeed'),
                               (self._wind_direction, 'WindDirection')):
                if value is not None:
                    xml_value = ET.SubElement(xml_conv, tag)
                    xml_value.text = str(value)
        # write the radiation record with its SteadyState constants
        if self._radiation_model is not None:
            xml_rad = ET.SubElement(xml_cond, 'Radiation')
            xml_model = ET.SubElement(xml_rad, 'Model')
            xml_model.text = self.radiation_model
            for value, tag in (
                    (self._radiation_temperature, 'Temperature'),
                    (self._surface_emissivity, 'SurfaceEmissivity'),
                    (self._view_factor, 'ViewFactor'),
                    (self._hr, 'hr')):
                if value is not None:
                    xml_value = ET.SubElement(xml_rad, tag)
                    xml_value.text = str(value)
        # write the solar record
        if self._solar_radiation is not None or self._absorptance is not None:
            xml_solar = ET.SubElement(xml_cond, 'Solar')
            for value, tag in ((self._solar_radiation, 'SolarRadiation'),
                               (self._absorptance, 'Absorptance')):
                if value is not None:
                    xml_value = ET.SubElement(xml_solar, tag)
                    xml_value.text = str(value)
        # write the driving flags and SteadyState constant values
        xml_use_flux = ET.SubElement(xml_cond, 'UseHeatFlux')
        xml_use_flux.text = 'true' if self.use_heat_flux else 'false'
        if self._heat_flux is not None:
            xml_flux = ET.SubElement(xml_cond, 'HeatFlux')
            xml_flux.text = str(self.heat_flux)
        xml_use_temp = ET.SubElement(xml_cond, 'UseTemperature')
        xml_use_temp.text = 'true' if self.use_temperature else 'false'
        if self._imposed_temperature is not None:
            xml_temp = ET.SubElement(xml_cond, 'Temperature')
            xml_temp.text = str(self.imposed_temperature)
        xml_use_hum = ET.SubElement(xml_cond, 'UseHumidity')
        xml_use_hum.text = 'true' if self.use_humidity else 'false'
        if self._imposed_humidity is not None:
            xml_hum = ET.SubElement(xml_cond, 'Humidity')
            xml_hum.text = str(self.imposed_humidity)
        xml_color = ET.SubElement(xml_cond, 'Color')
        xml_color.text = self.color.to_hex().replace('#', '0x')
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
        """Transient dictionary representation."""
        base = {
            'type': 'Transient',
            'identifier': self.identifier,
            'bc_type': self.bc_type,
            'bc_model': self.bc_model,
            'convection_model': self.convection_model
        }
        if self._radiation_model is not None:
            base['radiation_model'] = self.radiation_model
        if self._timesteps is not None:
            base['timesteps'] = {
                str(index): dict(step)
                for index, step in self._timesteps.items()}
        scalar_keys = (
            ('temperature', self._temperature),
            ('film_coefficient', self._film_coefficient),
            ('wind_speed', self._wind_speed),
            ('wind_direction', self._wind_direction),
            ('heat_flux', self._heat_flux),
            ('imposed_temperature', self._imposed_temperature),
            ('imposed_humidity', self._imposed_humidity),
            ('radiation_temperature', self._radiation_temperature),
            ('surface_emissivity', self._surface_emissivity),
            ('view_factor', self._view_factor),
            ('hr', self._hr),
            ('solar_radiation', self._solar_radiation),
            ('absorptance', self._absorptance),
            ('timestep_file_name', self._timestep_file_name),
            ('surface_tilt', self._surface_tilt),
            ('surface_length', self._surface_length),
            ('building_width', self._building_width),
            ('building_height', self._building_height))
        for key, value in scalar_keys:
            if value is not None:
                base[key] = value
        if self._use_heat_flux:
            base['use_heat_flux'] = self.use_heat_flux
        if self._use_temperature:
            base['use_temperature'] = self.use_temperature
        if self._use_humidity:
            base['use_humidity'] = self.use_humidity
        if self._display_name is not None:
            base['display_name'] = self.display_name
        base['protected'] = self._protected
        base['color'] = self.color.to_hex()
        if self._project_tag is not None:
            base['project_tag'] = self.project_tag
        if self._user_data is not None:
            base['user_data'] = self.user_data
        return base

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        timesteps = None
        if self._timesteps is not None:
            timesteps = tuple(
                (index, tuple(sorted(step.items())))
                for index, step in sorted(self._timesteps.items()))
        return (self.identifier, self.bc_type, self.bc_model,
                self.convection_model, self.radiation_model, timesteps,
                self.temperature, self.film_coefficient, self.wind_speed,
                self.wind_direction, self.use_heat_flux, self.heat_flux,
                self.use_temperature, self.imposed_temperature,
                self.use_humidity, self.imposed_humidity,
                self.radiation_temperature, self.surface_emissivity,
                self.view_factor, self.hr, self.solar_radiation,
                self.absorptance, self.timestep_file_name, self.surface_tilt,
                self.surface_length, self.building_width, self.building_height)

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, Transient) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __copy__(self):
        driven = self._convection_driven()
        new_cond = self.__class__(
            self._bc_type, self._bc_model,
            self._convection_model if driven else None,
            self._radiation_model if driven else None,
            dict((i, dict(s)) for i, s in self._timesteps.items())
            if self._timesteps is not None else None,
            self._temperature, self._film_coefficient, self._wind_speed,
            self._wind_direction, self._use_heat_flux, self._heat_flux,
            self._use_temperature, self._imposed_temperature,
            self._use_humidity, self._imposed_humidity,
            self._radiation_temperature, self._surface_emissivity,
            self._view_factor, self._hr, self._solar_radiation,
            self._absorptance, self._timestep_file_name, self._surface_tilt,
            self._surface_length, self._building_width, self._building_height,
            self.identifier)
        if not driven:  # restore inert model declarations verbatim
            new_cond._convection_model = self._convection_model
            new_cond._radiation_model = self._radiation_model
        new_cond._display_name = self._display_name
        new_cond._color = self._color
        new_cond._protected = self._protected
        new_cond._project_tag = self._project_tag
        new_cond._user_data = None if self._user_data is None \
            else self._user_data.copy()
        return new_cond

    def __repr__(self):
        return 'Transient THERM Condition: {}'.format(self.display_name)


def _placeholder_timesteps(bc_type):
    """Return a full-key timestep dict so from_therm_xml can construct.

    The placeholder satisfies every model's required keys and is replaced or
    dropped by from_therm_xml before the object is returned.
    """
    if bc_type == 'Transient':
        return {1: dict((key, 0) for key in Transient._TIMESTEP_KEYS)}
    return None
