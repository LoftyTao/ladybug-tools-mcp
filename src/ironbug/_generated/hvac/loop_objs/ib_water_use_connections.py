"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_WaterUseConnections(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_WaterUseConnections'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_WaterUseConnections.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_WaterUseConnections_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'WaterUseEquips',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'HotWaterSupplyTemperatureSchedule',
        'ColdWaterSupplyTemperatureSchedule',
        'DrainWaterHeatExchangerType',
        'DrainWaterHeatExchangerDestination',
        'DrainWaterHeatExchangerUFactorTimesArea',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'DrainWaterHeatExchangerDestination': 'str',
        'DrainWaterHeatExchangerType': 'str',
        'DrainWaterHeatExchangerUFactorTimesArea': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'ColdWaterSupplyTemperatureSchedule': 'IB_Schedule',
        'HotWaterSupplyTemperatureSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'WaterUseEquips': 'List<IB_WaterUseEquipment>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_WaterUseConnections'] = PydanticField(default='IB_WaterUseConnections')
    WaterUseEquips: list[IB_WaterUseEquipment] | None = PydanticField(default=None)

__all__ = [
    'IB_WaterUseConnections',
]
