"""Top-level Ironbug HVAC system object."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ironbug.hvac._base import IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject
from ironbug.hvac.loops import IB_AirLoopHVAC, IB_PlantLoop


class IB_HVACSystem(IronbugSourceMixin, IB_ModelObject):
    """Ironbug HVAC system container; no direct EnergyPlus object."""

    SOURCE_CLASS: ClassVar[str] = "IB_HVACSystem"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/IB_HVACSystem.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None

    AirLoops: list[IB_AirLoopHVAC] = Field(default_factory=list)
    PlantLoops: list[IB_PlantLoop] = Field(default_factory=list)
