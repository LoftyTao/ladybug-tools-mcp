"""Ironbug HVAC loop component objects."""

from __future__ import annotations

from typing import ClassVar

from ironbug.hvac._base import IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject


class IB_CoilCoolingWater(IronbugSourceMixin, IB_ModelObject):
    """Ironbug wrapper for EnergyPlus `Coil:Cooling:Water`."""

    SOURCE_CLASS: ClassVar[str] = "IB_CoilCoolingWater"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/LoopObjs/IB_CoilCoolingWater.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = "Coil:Cooling:Water"
    OPENSTUDIO_CLASS: ClassVar[str | None] = "CoilCoolingWater"


class IB_CoilHeatingWater(IronbugSourceMixin, IB_ModelObject):
    """Ironbug wrapper for EnergyPlus `Coil:Heating:Water`."""

    SOURCE_CLASS: ClassVar[str] = "IB_CoilHeatingWater"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/LoopObjs/IB_CoilHeatingWater.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = "Coil:Heating:Water"
    OPENSTUDIO_CLASS: ClassVar[str | None] = "CoilHeatingWater"


class IB_FanVariableVolume(IronbugSourceMixin, IB_ModelObject):
    """Ironbug wrapper for EnergyPlus `Fan:VariableVolume`."""

    SOURCE_CLASS: ClassVar[str] = "IB_FanVariableVolume"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/LoopObjs/IB_FanVariableVolume.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = "Fan:VariableVolume"
    OPENSTUDIO_CLASS: ClassVar[str | None] = "FanVariableVolume"
