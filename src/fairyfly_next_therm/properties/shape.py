# coding=utf-8
"""Shape Therm Properties."""
from fairyfly.checkdup import is_equivalent

from ..material.solid import SolidMaterial
from ..material.hygrothermal import HygrothermalMaterial
from ..material.cavity import CavityMaterial
from ..material.dictutil import dict_to_material
from ..lib.materials import concrete


class ShapeThermProperties(object):
    """Therm Properties for Fairyfly-Next Shape.

    Args:
        host: A fairyfly Shape object that hosts these properties.
        material: An optional Material object to set the conductive properties
            of the Shape. The default is set to a generic concrete material.

    Properties:
        * host
        * material
    """
    __slots__ = ('_host', '_material')

    def __init__(self, host, material=None):
        """Initialize Shape THERM properties."""
        self._host = host
        self.material = material

    @property
    def host(self):
        """Get the Shape object hosting these properties."""
        return self._host

    @property
    def material(self):
        """Get or set a THERM Material for the shape."""
        if self._material:  # set by user
            return self._material
        return concrete

    @material.setter
    def material(self, value):
        if value is not None:
            if not isinstance(value, (SolidMaterial, HygrothermalMaterial,
                                      CavityMaterial)):
                raise ValueError(
                    'Expected SolidMaterial, HygrothermalMaterial or '
                    'CavityMaterial. Got {}.'.format(type(value)))
            value.lock()  # lock editing in case material has multiple references
        self._material = value

    @classmethod
    def from_dict(cls, data, host):
        """Create ShapeThermProperties from a dictionary.

        Note that the dictionary must be a non-abridged version for this
        classmethod to work.

        Args:
            data: A dictionary representation of ShapeThermProperties with the
                format below.
            host: A Shape object that hosts these properties.

        .. code-block:: python

            {
            "type": 'ShapeThermProperties',
            "material": {},  # A SolidMaterial or CavityMaterial dictionary
            }
        """
        assert data['type'] == 'ShapeThermProperties', \
            'Expected ShapeThermProperties. Got {}.'.format(data['type'])
        new_prop = cls(host)
        if 'material' in data and data['material'] is not None:
            new_prop.material = dict_to_material(data['material'])
        return new_prop

    def apply_properties_from_dict(self, abridged_data, materials):
        """Apply properties from a ShapeThermPropertiesAbridged dictionary.

        Args:
            abridged_data: A ShapeThermPropertiesAbridged dictionary (typically
                coming from a Model).
            materials: A dictionary of materials with material identifiers
                as keys, which will be used to re-assign materials.
        """
        if 'material' in abridged_data and abridged_data['material'] is not None:
            try:
                self.material = materials[abridged_data['material']]
            except KeyError:
                raise ValueError('Shape material "{}" was not found in '
                                 'materials.'.format(abridged_data['material']))

    def to_dict(self, abridged=False):
        """Return therm properties as a dictionary.

        Args:
            abridged: Boolean to note whether the full dictionary describing the
                object should be returned (False) or just an abridged version (True).
                Default: False.
        """
        base = {'therm': {}}
        base['therm']['type'] = 'ShapeThermProperties' if not \
            abridged else 'ShapeThermPropertiesAbridged'
        if self._material is not None:
            base['therm']['material'] = \
                self._material.identifier if abridged else self._material.to_dict()
        return base

    def duplicate(self, new_host=None):
        """Get a copy of this object.

        Args:
            new_host: A new Shape object that hosts these properties.
                If None, the properties will be duplicated with the same host.
        """
        _host = new_host or self._host
        new_obj = ShapeThermProperties(_host)
        # assign directly instead of the setter so that duplicating shares the
        # same Material object without re-locking it; a copy must not mutate
        # the lock state of a resource it does not own
        new_obj._material = self._material
        return new_obj

    def is_equivalent(self, other):
        """Check to see if these therm properties are equivalent to another object.

        This will only be True if all properties match (except for the host) and
        will otherwise be False.
        """
        if not is_equivalent(self._material, other._material):
            return False
        return True

    def ToString(self):
        return self.__repr__()

    def __repr__(self):
        return 'Shape Therm Properties: [host: {}]'.format(self.host.display_name)
