"""Ironbug HVAC branch collection objects."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ironbug.hvac._base import IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject


class IB_AirLoopBranches(IronbugSourceMixin, IB_ModelObject):
    """Ironbug air loop branch collection; no direct EnergyPlus object."""

    SOURCE_CLASS: ClassVar[str] = "IB_AirLoopBranches"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/Loops/IB_AirLoopBranches.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None

    Branches: list[IB_ModelObject] = Field(default_factory=list)

class IB_PlantLoopBranches(IronbugSourceMixin, IB_ModelObject):
    """Ironbug plant loop branch collection; no direct EnergyPlus object."""

    SOURCE_CLASS: ClassVar[str] = "IB_PlantLoopBranches"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/Loops/IB_PlantLoopBranches.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None

    Branches: list[IB_ModelObject] = Field(default_factory=list)
