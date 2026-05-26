"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_HVACSystem(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_HVACSystem'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/IB_HVACSystem.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = ()
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = None
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'DisplayName',
        'AirLoops',
        'PlantLoops',
        'VariableRefrigerantFlows',
        'IBVersion',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = (
        'DisplayName',
        'AirLoops',
        'PlantLoops',
        'VariableRefrigerantFlows',
        'IBVersion',
    )
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = (
        'AirLoops',
        'PlantLoops',
        'VariableRefrigerantFlows',
    )
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = (
        'IBVersion',
    )
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'AirLoops': 'List<IB_AirLoopHVAC>',
        'DisplayName': 'string',
        'IBVersion': 'string',
        'PlantLoops': 'List<IB_PlantLoop>',
        'VariableRefrigerantFlows': 'List<IB_AirConditionerVariableRefrigerantFlow>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {
        'AirLoops': 'List<IB_AirLoopHVAC>',
        'DisplayName': 'string',
        'IBVersion': 'string',
        'PlantLoops': 'List<IB_PlantLoop>',
        'VariableRefrigerantFlows': 'List<IB_AirConditionerVariableRefrigerantFlow>',
    }
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_HVACSystem'] = PydanticField(default='IB_HVACSystem')
    AirLoops: list[IB_AirLoopHVAC] | None = PydanticField(default=None)
    PlantLoops: list[IB_PlantLoop] | None = PydanticField(default=None)
    VariableRefrigerantFlows: list[IB_AirConditionerVariableRefrigerantFlow] | None = PydanticField(default=None)

__all__ = [
    'IB_HVACSystem',
]
