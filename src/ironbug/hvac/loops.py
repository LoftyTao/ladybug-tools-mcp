"""Ironbug HVAC loop objects."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from ironbug.hvac._base import IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject
from ironbug.hvac.branches import IB_AirLoopBranches, IB_PlantLoopBranches


class IB_AirLoopHVAC(IronbugSourceMixin, IB_ModelObject):
    """Ironbug wrapper for EnergyPlus `AirLoopHVAC`."""

    SOURCE_CLASS: ClassVar[str] = "IB_AirLoopHVAC"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/Loops/IB_AirLoopHVAC.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = "AirLoopHVAC"
    OPENSTUDIO_CLASS: ClassVar[str | None] = "AirLoopHVAC"

    SupplyComponents: list[IB_ModelObject] = Field(default_factory=list)
    DemandComponents: list[IB_ModelObject] = Field(default_factory=list)
    Branches: IB_AirLoopBranches | None = None


class IB_PlantLoop(IronbugSourceMixin, IB_ModelObject):
    """Ironbug wrapper for EnergyPlus `PlantLoop`."""

    SOURCE_CLASS: ClassVar[str] = "IB_PlantLoop"
    SOURCE_PATH: ClassVar[str] = "src/Ironbug.HVAC/Loops/IB_PlantLoop.cs"
    ENERGYPLUS_OBJECT: ClassVar[str | None] = "PlantLoop"
    OPENSTUDIO_CLASS: ClassVar[str | None] = "PlantLoop"

    SupplyComponents: list[IB_ModelObject] = Field(default_factory=list)
    DemandComponents: list[IB_ModelObject] = Field(default_factory=list)
    Branches: IB_PlantLoopBranches | None = None
