"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilCoolingDXMultiSpeedStageData(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilCoolingDXMultiSpeedStageData'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilCoolingDXMultiSpeedStageData.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ModelObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilCoolingDXMultiSpeedStageData_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'GrossRatedTotalCoolingCapacity',
        'GrossRatedSensibleHeatRatio',
        'GrossRatedCoolingCOP',
        'RatedAirFlowRate',
        'RatedEvaporatorFanPowerPerVolumeFlowRate',
        'RatedEvaporatorFanPowerPerVolumeFlowRate2017',
        'RatedEvaporatorFanPowerPerVolumeFlowRate2023',
        'TotalCoolingCapacityFunctionofTemperatureCurve',
        'TotalCoolingCapacityFunctionofFlowFractionCurve',
        'EnergyInputRatioFunctionofTemperatureCurve',
        'EnergyInputRatioFunctionofFlowFractionCurve',
        'PartLoadFractionCorrelationCurve',
        'NominalTimeforCondensateRemovaltoBegin',
        'RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity',
        'MaximumCyclingRate',
        'LatentCapacityTimeConstant',
        'RatedWasteHeatFractionofPowerInput',
        'WasteHeatFunctionofTemperatureCurve',
        'EvaporativeCondenserEffectiveness',
        'EvaporativeCondenserAirFlowRate',
        'RatedEvaporativeCondenserPumpPowerConsumption',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'EvaporativeCondenserAirFlowRate': 'float',
        'EvaporativeCondenserEffectiveness': 'float',
        'GrossRatedCoolingCOP': 'float',
        'GrossRatedSensibleHeatRatio': 'float',
        'GrossRatedTotalCoolingCapacity': 'float',
        'LatentCapacityTimeConstant': 'float',
        'MaximumCyclingRate': 'float',
        'NominalTimeforCondensateRemovaltoBegin': 'float',
        'RatedAirFlowRate': 'float',
        'RatedEvaporativeCondenserPumpPowerConsumption': 'float',
        'RatedEvaporatorFanPowerPerVolumeFlowRate': 'str | float | int | bool',
        'RatedEvaporatorFanPowerPerVolumeFlowRate2017': 'float',
        'RatedEvaporatorFanPowerPerVolumeFlowRate2023': 'float',
        'RatedWasteHeatFractionofPowerInput': 'float',
        'RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'EnergyInputRatioFunctionofFlowFractionCurve': 'IB_Curve',
        'EnergyInputRatioFunctionofTemperatureCurve': 'IB_Curve',
        'PartLoadFractionCorrelationCurve': 'IB_Curve',
        'TotalCoolingCapacityFunctionofFlowFractionCurve': 'IB_Curve',
        'TotalCoolingCapacityFunctionofTemperatureCurve': 'IB_Curve',
        'WasteHeatFunctionofTemperatureCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilCoolingDXMultiSpeedStageData'] = PydanticField(default='IB_CoilCoolingDXMultiSpeedStageData')

__all__ = [
    'IB_CoilCoolingDXMultiSpeedStageData',
]
