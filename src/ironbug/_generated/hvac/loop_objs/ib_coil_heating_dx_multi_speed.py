"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilHeatingDXMultiSpeed(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilHeatingDXMultiSpeed'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilHeatingDXMultiSpeed.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilDX',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilHeatingDXMultiSpeed_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'Stages',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation',
        'OutdoorDryBulbTemperaturetoTurnOnCompressor',
        'CrankcaseHeaterCapacity',
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve',
        'MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation',
        'DefrostEnergyInputRatioFunctionofTemperatureCurve',
        'MaximumOutdoorDryBulbTemperatureforDefrostOperation',
        'DefrostStrategy',
        'DefrostControl',
        'DefrostTimePeriodFraction',
        'ResistiveDefrostHeaterCapacity',
        'ApplyPartLoadFractiontoSpeedsGreaterthan1',
        'FuelType',
        'RegionnumberforCalculatingHSPF',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ApplyPartLoadFractiontoSpeedsGreaterthan1': 'bool | str',
        'CrankcaseHeaterCapacity': 'float',
        'DefrostControl': 'str',
        'DefrostStrategy': 'str',
        'DefrostTimePeriodFraction': 'float',
        'FuelType': 'str',
        'MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation': 'float',
        'MaximumOutdoorDryBulbTemperatureforDefrostOperation': 'float',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation': 'float',
        'OutdoorDryBulbTemperaturetoTurnOnCompressor': 'float',
        'RegionnumberforCalculatingHSPF': 'int',
        'ResistiveDefrostHeaterCapacity': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve': 'IB_Curve',
        'DefrostEnergyInputRatioFunctionofTemperatureCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'Stages': 'List<IB_CoilHeatingDXMultiSpeedStageData>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilHeatingDXMultiSpeed'] = PydanticField(default='IB_CoilHeatingDXMultiSpeed')
    Stages: list[IB_CoilHeatingDXMultiSpeedStageData] | None = PydanticField(default=None)

__all__ = [
    'IB_CoilHeatingDXMultiSpeed',
]
