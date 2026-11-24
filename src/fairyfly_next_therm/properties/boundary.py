# coding=utf-8
"""Boundary Therm Properties."""
from fairyfly.checkdup import is_equivalent

from ..condition.steadystate import SteadyState
from ..condition.transient import Transient
from ..condition.dictutil import dict_to_condition
from ..lib.conditions import exterior


class BoundaryThermProperties(object):
    """Therm Properties for Fairyfly-Next Boundary.

    Args:
        host: A fairyfly Boundary object that hosts these properties.
        condition: An optional Condition object to set the conductive properties
            of the Boundary. The default is set to a generic concrete condition.
        u_factor_tag: An optional text string for to define a U-Factor tag along
            the boundary condition. This tag is used tell THERM the boundary on
            which a net U-Value shall be computed. Typical values to input here,
            which are recognizable in LBNL WINDOW include the following.

            * Frame
            * Edge
            * Spacer
            * ShadeInETag
            * ShadeOutETag
            * SHGC Exterior
            * New

    Properties:
        * host
        * condition
        * u_factor_tag
    """
    __slots__ = ('_host', '_condition', '_u_factor_tag')

    def __init__(self, host, condition=None, u_factor_tag=None):
        """Initialize Boundary THERM properties."""
        self._host = host
        self.condition = condition
        self.u_factor_tag = u_factor_tag

    @property
    def host(self):
        """Get the Boundary object hosting these properties."""
        return self._host

    @property
    def condition(self):
        """Get or set a THERM Condition for the boundary."""
        if self._condition:  # set by user
            return self._condition
        return exterior

    @condition.setter
    def condition(self, value):
        if value is not None:
            if not isinstance(value, (SteadyState, Transient)):
                raise ValueError(
                    'Expected SteadyState or Transient. Got {}.'.format(
                        type(value)))
            value.lock()  # lock editing in case condition has multiple references
        self._condition = value

    @property
    def u_factor_tag(self):
        """Get or set a string for to define a U-Factor tag along the boundary condition.
        """
        return self._u_factor_tag

    @u_factor_tag.setter
    def u_factor_tag(self, value):
        if value is not None:
            try:
                value = str(value)
            except UnicodeEncodeError:  # Python 2 machine lacking the character set
                pass  # keep it as unicode
        self._u_factor_tag = value

    @classmethod
    def from_dict(cls, data, host):
        """Create BoundaryThermProperties from a dictionary.

        Note that the dictionary must be a non-abridged version for this
        classmethod to work.

        Args:
            data: A dictionary representation of BoundaryThermProperties with the
                format below.
            host: A Boundary object that hosts these properties.

        .. code-block:: python

            {
            "type": 'BoundaryThermProperties',
            "condition": {},  # A SteadyState dictionary
            "u_factor_tag": "Frame"  # text for the u-factor tag
            }
        """
        assert data['type'] == 'BoundaryThermProperties', \
            'Expected BoundaryThermProperties. Got {}.'.format(data['type'])
        new_prop = cls(host)
        if 'condition' in data and data['condition'] is not None:
            new_prop.condition = dict_to_condition(data['condition'])
        if 'u_factor_tag' in data and data['u_factor_tag'] is not None:
            new_prop.u_factor_tag = data['u_factor_tag']
        return new_prop

    def apply_properties_from_dict(self, abridged_data, conditions):
        """Apply properties from a BoundaryThermPropertiesAbridged dictionary.

        Args:
            abridged_data: A BoundaryThermPropertiesAbridged dictionary (typically
                coming from a Model).
            conditions: A dictionary of conditions with condition identifiers
                as keys, which will be used to re-assign conditions.
        """
        if 'condition' in abridged_data and abridged_data['condition'] is not None:
            try:
                self.condition = conditions[abridged_data['condition']]
            except KeyError:
                raise ValueError('Boundary condition "{}" was not found in '
                                 'conditions.'.format(abridged_data['condition']))
        if 'u_factor_tag' in abridged_data and abridged_data['u_factor_tag'] is not None:
            self.u_factor_tag = abridged_data['u_factor_tag']

    def to_dict(self, abridged=False):
        """Return therm properties as a dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
        """
        base = {'therm': {}}
        base['therm']['type'] = 'BoundaryThermProperties' if not \
            abridged else 'BoundaryThermPropertiesAbridged'
        if self._condition is not None:
            base['therm']['condition'] = \
                self._condition.identifier if abridged else self._condition.to_dict()
        if self.u_factor_tag is not None:
            base['therm']['u_factor_tag'] = self.u_factor_tag
        return base

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        Args:
            new_host: A new Boundary object that hosts these properties.
                If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        new_obj = BoundaryThermProperties(_host)
        # assign directly instead of the setter so that duplicating shares the
        # same Condition object without re-locking it; a copy must not mutate
        # the lock state of a resource it does not own
        new_obj._condition = self._condition
        new_obj._u_factor_tag = self._u_factor_tag
        return new_obj

    def is_equivalent(self, other):
        """Check to see if these therm properties are equivalent to another object.

        This will only be True if all properties match (except for the host) and
        will otherwise be False.
        """
        if not is_equivalent(self._condition, other._condition):
            return False
        if self._u_factor_tag != other._u_factor_tag:
            return False
        return True

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Boundary Therm Properties: [host: {}]'.format(self.host.display_name)
