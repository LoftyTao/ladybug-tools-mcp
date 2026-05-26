"""Ironbug HVAC thermal zone objects."""

from __future__ import annotations

from typing import ClassVar

from ironbug.hvac._base import IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject


class IB_ThermalZone(IronbugSourceMixin, IB_ModelObject):
    """Ironbug thermal zone wrapper for EnergyPlus `Zone`."""

    SOURCE_CLASS: ClassVar[str] = "IB_ThermalZone"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/ZoneEquipments/IB_ThermalZone.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = "Zone"
    OPENSTUDIO_CLASS: ClassVar[str | None] = "ThermalZone"
