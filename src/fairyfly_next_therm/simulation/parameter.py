# coding=utf-8
"""Complete set of THERM Simulation Settings."""
from __future__ import division

from .mesh import MeshControl
from .exposure import ModelExposure
from .transient import TransientCalculation


class SimulationParameter(object):
    """Complete set of Therm Simulation Settings.

    Args:
        mesh: A MeshControl that lists the desired meshing procedure. If None,
            default meshing control will be automatically generated. (Default: None).
        exposure: A ModelExposure that describes the model location in a building.
            If None, default exposure will be automatically generated. (Default: None).
        transient: A TransientCalculation that describes the transient mode
            and engine parameters. If None, the simulation is written as a
            steady-state calculation and the steady-state serialization is
            unchanged. (Default: None).

    Properties:
        * mesh
        * exposure
        * transient
    """
    __slots__ = ('_mesh', '_exposure', '_transient')

    def __init__(self, mesh=None, exposure=None, transient=None):
        """Initialize SimulationParameter."""
        self.mesh = mesh
        self.exposure = exposure
        self.transient = transient

    @property
    def mesh(self):
        """Get or set a MeshControl object for the simulation meshing procedure."""
        return self._mesh

    @mesh.setter
    def mesh(self, value):
        if value is not None:
            assert isinstance(value, MeshControl), 'Expected MeshControl ' \
                'for SimulationParameter output. Got {}.'.format(type(value))
            self._mesh = value
        else:
            self._mesh = MeshControl()

    @property
    def exposure(self):
        """Get or set a ModelExposure object that describes the model location in a building.
        """
        return self._exposure

    @exposure.setter
    def exposure(self, value):
        if value is not None:
            assert isinstance(value, ModelExposure), 'Expected ModelExposure ' \
                'for SimulationParameter output. Got {}.'.format(type(value))
            self._exposure = value
        else:
            self._exposure = ModelExposure()

    @property
    def transient(self):
        """Get or set a TransientCalculation object or None for steady-state."""
        return self._transient

    @transient.setter
    def transient(self, value):
        if value is not None:
            if not isinstance(value, TransientCalculation):
                raise ValueError(
                    'Expected TransientCalculation for SimulationParameter '
                    'transient. Got {}.'.format(type(value)))
        self._transient = value

    @classmethod
    def from_dict(cls, data):
        """Create a SimulationParameter object from a dictionary.

        Args:
            data: A SimulationParameter dictionary in following the format below.

        .. code-block:: python

            {
            "type": "SimulationParameter",
            "mesh": {} # Fairyfly-Next THERM MeshControl dictionary
            "exposure": {}  # Fairyfly-Next ModelExposure dictionary
            "transient": {}  # optional TransientCalculation dictionary
            }
        """
        assert data['type'] == 'SimulationParameter', \
            'Expected SimulationParameter dictionary. Got {}.'.format(data['type'])
        mesh = None
        if 'mesh' in data and data['mesh'] is not None:
            mesh = MeshControl.from_dict(data['mesh'])
        exposure = None
        if 'exposure' in data and data['exposure'] is not None:
            exposure = ModelExposure.from_dict(data['exposure'])
        transient = None
        if 'transient' in data and data['transient'] is not None:
            transient = TransientCalculation.from_dict(data['transient'])
        return cls(mesh, exposure, transient)

    def to_dict(self):
        """SimulationParameter dictionary representation."""
        base = {
            'type': 'SimulationParameter',
            'mesh': self.mesh.to_dict(),
            'exposure': self.exposure.to_dict()
        }
        if self._transient is not None:
            base['transient'] = self._transient.to_dict()
        return base

    def duplicate(self):
        """Get a copy of this object."""
        return self.__copy__()

    def ToString(self):
        """Overwrite .NET ToString."""
        return self.__repr__()

    def __copy__(self):
        return SimulationParameter(
            self.mesh.duplicate(), self.exposure.duplicate(),
            None if self._transient is None else self._transient.duplicate())

    def __key(self):
        """A tuple based on the object properties, useful for hashing."""
        return (hash(self.mesh), hash(self.exposure),
                None if self._transient is None else hash(self._transient))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return isinstance(other, SimulationParameter) and self.__key() == other.__key()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return 'Therm SimulationParameter:'
