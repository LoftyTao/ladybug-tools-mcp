"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilPerformanceDXCooling(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilPerformanceDXCooling'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilPerformanceDXCooling.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ModelObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilPerformanceDXCooling_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'GrossRatedTotalCoolingCapacity',
        'GrossRatedSensibleHeatRatio',
        'GrossRatedCoolingCOP',
        'RatedAirFlowRate',
        'FractionofAirFlowBypassedAroundCoil',
        'TotalCoolingCapacityFunctionofTemperatureCurve',
        'TotalCoolingCapacityFunctionofFlowFractionCurve',
        'EnergyInputRatioFunctionofTemperatureCurve',
        'EnergyInputRatioFunctionofFlowFractionCurve',
        'PartLoadFractionCorrelationCurve',
        'NominalTimeforCondensateRemovaltoBegin',
        'RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity',
        'MaximumCyclingRate',
        'LatentCapacityTimeConstant',
        'CondenserType',
        'EvaporativeCondenserEffectiveness',
        'EvaporativeCondenserAirFlowRate',
        'EvaporativeCondenserPumpRatedPowerConsumption',
        'SensibleHeatRatioFunctionofTemperatureCurve',
        'SensibleHeatRatioFunctionofFlowFractionCurve',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CondenserType': 'str',
        'EvaporativeCondenserAirFlowRate': 'float',
        'EvaporativeCondenserEffectiveness': 'float',
        'EvaporativeCondenserPumpRatedPowerConsumption': 'float',
        'FractionofAirFlowBypassedAroundCoil': 'float',
        'GrossRatedCoolingCOP': 'float',
        'GrossRatedSensibleHeatRatio': 'float',
        'GrossRatedTotalCoolingCapacity': 'float',
        'LatentCapacityTimeConstant': 'float',
        'MaximumCyclingRate': 'float',
        'NominalTimeforCondensateRemovaltoBegin': 'float',
        'RatedAirFlowRate': 'float',
        'RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'EnergyInputRatioFunctionofFlowFractionCurve': 'IB_Curve',
        'EnergyInputRatioFunctionofTemperatureCurve': 'IB_Curve',
        'PartLoadFractionCorrelationCurve': 'IB_Curve',
        'SensibleHeatRatioFunctionofFlowFractionCurve': 'IB_Curve',
        'SensibleHeatRatioFunctionofTemperatureCurve': 'IB_Curve',
        'TotalCoolingCapacityFunctionofFlowFractionCurve': 'IB_Curve',
        'TotalCoolingCapacityFunctionofTemperatureCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilPerformanceDXCooling'] = PydanticField(default='IB_CoilPerformanceDXCooling')

__all__ = [
    'IB_CoilPerformanceDXCooling',
]
