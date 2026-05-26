"""Ironbug HVAC setpoint manager objects."""

from __future__ import annotations

from typing import ClassVar

from ironbug.hvac._base import IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject


class IB_SetpointManagerMixedAir(IronbugSourceMixin, IB_ModelObject):
    """Ironbug wrapper for EnergyPlus `SetpointManager:MixedAir`."""

    SOURCE_CLASS: ClassVar[str] = "IB_SetpointManagerMixedAir"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/SetpointManagers/IB_SetpointManagerMixedAir.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = "SetpointManager:MixedAir"
    OPENSTUDIO_CLASS: ClassVar[str | None] = "SetpointManagerMixedAir"
