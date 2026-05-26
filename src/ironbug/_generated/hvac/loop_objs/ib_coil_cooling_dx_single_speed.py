"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilCoolingDXSingleSpeed(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilCoolingDXSingleSpeed'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilCoolingDXSingleSpeed.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilDX',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilCoolingDXSingleSpeed_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'RatedCOP',
        'RatedEvaporatorFanPowerPerVolumeFlowRate',
        'RatedEvaporatorFanPowerPerVolumeFlowRate2017',
        'RatedEvaporatorFanPowerPerVolumeFlowRate2023',
        'TotalCoolingCapacityFunctionOfTemperatureCurve',
        'TotalCoolingCapacityFunctionOfFlowFractionCurve',
        'EnergyInputRatioFunctionOfTemperatureCurve',
        'EnergyInputRatioFunctionOfFlowFractionCurve',
        'PartLoadFractionCorrelationCurve',
        'NominalTimeForCondensateRemovalToBegin',
        'RatioOfInitialMoistureEvaporationRateAndSteadyStateLatentCapacity',
        'MaximumCyclingRate',
        'LatentCapacityTimeConstant',
        'CondenserType',
        'EvaporativeCondenserEffectiveness',
        'EvaporativeCondenserAirFlowRate',
        'EvaporativeCondenserPumpRatedPowerConsumption',
        'CrankcaseHeaterCapacity',
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve',
        'MaximumOutdoorDryBulbTemperatureForCrankcaseHeaterOperation',
        'BasinHeaterCapacity',
        'BasinHeaterSetpointTemperature',
        'BasinHeaterOperatingSchedule',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation',
        'RatedTotalCoolingCapacity',
        'RatedSensibleHeatRatio',
        'RatedAirFlowRate',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'BasinHeaterCapacity': 'float',
        'BasinHeaterSetpointTemperature': 'float',
        'CondenserType': 'str',
        'CrankcaseHeaterCapacity': 'float',
        'EvaporativeCondenserAirFlowRate': 'float',
        'EvaporativeCondenserEffectiveness': 'float',
        'EvaporativeCondenserPumpRatedPowerConsumption': 'float',
        'LatentCapacityTimeConstant': 'float',
        'MaximumCyclingRate': 'float',
        'MaximumOutdoorDryBulbTemperatureForCrankcaseHeaterOperation': 'float',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation': 'float',
        'NominalTimeForCondensateRemovalToBegin': 'float',
        'RatedAirFlowRate': 'float',
        'RatedCOP': 'float',
        'RatedEvaporatorFanPowerPerVolumeFlowRate': 'str | float | int | bool',
        'RatedEvaporatorFanPowerPerVolumeFlowRate2017': 'float',
        'RatedEvaporatorFanPowerPerVolumeFlowRate2023': 'float',
        'RatedSensibleHeatRatio': 'float',
        'RatedTotalCoolingCapacity': 'float',
        'RatioOfInitialMoistureEvaporationRateAndSteadyStateLatentCapacity': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'BasinHeaterOperatingSchedule': 'IB_Schedule',
        'CrankcaseHeaterCapacityFunctionofTemperatureCurve': 'IB_Curve',
        'EnergyInputRatioFunctionOfFlowFractionCurve': 'IB_Curve',
        'EnergyInputRatioFunctionOfTemperatureCurve': 'IB_Curve',
        'PartLoadFractionCorrelationCurve': 'IB_Curve',
        'TotalCoolingCapacityFunctionOfFlowFractionCurve': 'IB_Curve',
        'TotalCoolingCapacityFunctionOfTemperatureCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilCoolingDXSingleSpeed'] = PydanticField(default='IB_CoilCoolingDXSingleSpeed')

__all__ = [
    'IB_CoilCoolingDXSingleSpeed',
]
