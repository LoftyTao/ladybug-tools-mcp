"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilHeatingDXSingleSpeed(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilHeatingDXSingleSpeed'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilHeatingDXSingleSpeed.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilDX',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilHeatingDXSingleSpeed_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'RatedTotalHeatingCapacity',
        'AvailabilitySchedule',
        'RatedCOP',
        'RatedAirFlowRate',
        'RatedSupplyFanPowerPerVolumeFlowRate',
        'RatedSupplyFanPowerPerVolumeFlowRate2017',
        'RatedSupplyFanPowerPerVolumeFlowRate2023',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation',
        'MaximumOutdoorDryBulbTemperatureforDefrostOperation',
        'CrankcaseHeaterCapacity',
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve',
        'MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation',
        'DefrostStrategy',
        'DefrostControl',
        'DefrostTimePeriodFraction',
        'ResistiveDefrostHeaterCapacity',
        'TotalHeatingCapacityFunctionofTemperatureCurve',
        'TotalHeatingCapacityFunctionofFlowFractionCurve',
        'EnergyInputRatioFunctionofTemperatureCurve',
        'EnergyInputRatioFunctionofFlowFractionCurve',
        'PartLoadFractionCorrelationCurve',
        'DefrostEnergyInputRatioFunctionofTemperatureCurve',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CrankcaseHeaterCapacity': 'float',
        'DefrostControl': 'str',
        'DefrostStrategy': 'str',
        'DefrostTimePeriodFraction': 'float',
        'MaximumOutdoorDryBulbTemperatureforCrankcaseHeaterOperation': 'float',
        'MaximumOutdoorDryBulbTemperatureforDefrostOperation': 'float',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation': 'float',
        'RatedAirFlowRate': 'float',
        'RatedCOP': 'float',
        'RatedSupplyFanPowerPerVolumeFlowRate': 'str | float | int | bool',
        'RatedSupplyFanPowerPerVolumeFlowRate2017': 'float',
        'RatedSupplyFanPowerPerVolumeFlowRate2023': 'float',
        'RatedTotalHeatingCapacity': 'float',
        'ResistiveDefrostHeaterCapacity': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve': 'IB_Curve',
        'DefrostEnergyInputRatioFunctionofTemperatureCurve': 'IB_Curve',
        'EnergyInputRatioFunctionofFlowFractionCurve': 'IB_Curve',
        'EnergyInputRatioFunctionofTemperatureCurve': 'IB_Curve',
        'PartLoadFractionCorrelationCurve': 'IB_Curve',
        'TotalHeatingCapacityFunctionofFlowFractionCurve': 'IB_Curve',
        'TotalHeatingCapacityFunctionofTemperatureCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilHeatingDXSingleSpeed'] = PydanticField(default='IB_CoilHeatingDXSingleSpeed')

__all__ = [
    'IB_CoilHeatingDXSingleSpeed',
]
