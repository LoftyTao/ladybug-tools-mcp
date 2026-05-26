"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilCoolingDXMultiSpeed(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilCoolingDXMultiSpeed'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilCoolingDXMultiSpeed.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilDX',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilCoolingDXMultiSpeed_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'Stages',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'CondenserType',
        'ApplyPartLoadFractiontoSpeedsGreaterthan1',
        'ApplyLatentDegradationtoSpeedsGreaterthan1',
        'CrankcaseHeaterCapacity',
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve',
        'MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation',
        'BasinHeaterCapacity',
        'BasinHeaterSetpointTemperature',
        'BasinHeaterOperatingSchedule',
        'FuelType',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ApplyLatentDegradationtoSpeedsGreaterthan1': 'bool | str',
        'ApplyPartLoadFractiontoSpeedsGreaterthan1': 'bool | str',
        'BasinHeaterCapacity': 'float',
        'BasinHeaterSetpointTemperature': 'float',
        'CondenserType': 'str',
        'CrankcaseHeaterCapacity': 'float',
        'FuelType': 'str',
        'MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation': 'float',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'BasinHeaterOperatingSchedule': 'IB_Schedule',
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'Stages': 'List<IB_CoilCoolingDXMultiSpeedStageData>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilCoolingDXMultiSpeed'] = PydanticField(default='IB_CoilCoolingDXMultiSpeed')
    Stages: list[IB_CoilCoolingDXMultiSpeedStageData] | None = PydanticField(default=None)

__all__ = [
    'IB_CoilCoolingDXMultiSpeed',
]
