"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilCoolingWaterToAirHeatPumpEquationFit(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilCoolingWaterToAirHeatPumpEquationFit'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilCoolingWaterToAirHeatPumpEquationFit.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilHeatingBasic',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_DualLoopObj',
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilCoolingWaterToAirHeatPumpEquationFit_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'RatedAirFlowRate',
        'RatedWaterFlowRate',
        'RatedTotalCoolingCapacity',
        'RatedSensibleCoolingCapacity',
        'RatedCoolingCoefficientofPerformance',
        'RatedEnteringWaterTemperature',
        'RatedEnteringAirDryBulbTemperature',
        'RatedEnteringAirWetBulbTemperature',
        'TotalCoolingCapacityCurve',
        'TotalCoolingCapacityCoefficient1',
        'TotalCoolingCapacityCoefficient2',
        'TotalCoolingCapacityCoefficient3',
        'TotalCoolingCapacityCoefficient4',
        'TotalCoolingCapacityCoefficient5',
        'SensibleCoolingCapacityCurve',
        'SensibleCoolingCapacityCoefficient1',
        'SensibleCoolingCapacityCoefficient2',
        'SensibleCoolingCapacityCoefficient3',
        'SensibleCoolingCapacityCoefficient4',
        'SensibleCoolingCapacityCoefficient5',
        'SensibleCoolingCapacityCoefficient6',
        'CoolingPowerConsumptionCurve',
        'CoolingPowerConsumptionCoefficient1',
        'CoolingPowerConsumptionCoefficient2',
        'CoolingPowerConsumptionCoefficient3',
        'CoolingPowerConsumptionCoefficient4',
        'CoolingPowerConsumptionCoefficient5',
        'PartLoadFractionCorrelationCurve',
        'NominalTimeforCondensateRemovaltoBegin',
        'RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity',
        'MaximumCyclingRate',
        'LatentCapacityTimeConstant',
        'FanDelayTime',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CoolingPowerConsumptionCoefficient1': 'str | float | int | bool',
        'CoolingPowerConsumptionCoefficient2': 'str | float | int | bool',
        'CoolingPowerConsumptionCoefficient3': 'str | float | int | bool',
        'CoolingPowerConsumptionCoefficient4': 'str | float | int | bool',
        'CoolingPowerConsumptionCoefficient5': 'str | float | int | bool',
        'FanDelayTime': 'float',
        'LatentCapacityTimeConstant': 'float',
        'MaximumCyclingRate': 'float',
        'NominalTimeforCondensateRemovaltoBegin': 'float',
        'RatedAirFlowRate': 'float',
        'RatedCoolingCoefficientofPerformance': 'float',
        'RatedEnteringAirDryBulbTemperature': 'float',
        'RatedEnteringAirWetBulbTemperature': 'float',
        'RatedEnteringWaterTemperature': 'float',
        'RatedSensibleCoolingCapacity': 'float',
        'RatedTotalCoolingCapacity': 'float',
        'RatedWaterFlowRate': 'float',
        'RatioofInitialMoistureEvaporationRateandSteadyStateLatentCapacity': 'float',
        'SensibleCoolingCapacityCoefficient1': 'str | float | int | bool',
        'SensibleCoolingCapacityCoefficient2': 'str | float | int | bool',
        'SensibleCoolingCapacityCoefficient3': 'str | float | int | bool',
        'SensibleCoolingCapacityCoefficient4': 'str | float | int | bool',
        'SensibleCoolingCapacityCoefficient5': 'str | float | int | bool',
        'SensibleCoolingCapacityCoefficient6': 'str | float | int | bool',
        'TotalCoolingCapacityCoefficient1': 'str | float | int | bool',
        'TotalCoolingCapacityCoefficient2': 'str | float | int | bool',
        'TotalCoolingCapacityCoefficient3': 'str | float | int | bool',
        'TotalCoolingCapacityCoefficient4': 'str | float | int | bool',
        'TotalCoolingCapacityCoefficient5': 'str | float | int | bool',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'CoolingPowerConsumptionCurve': 'IB_Curve',
        'PartLoadFractionCorrelationCurve': 'IB_Curve',
        'SensibleCoolingCapacityCurve': 'IB_Curve',
        'TotalCoolingCapacityCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilCoolingWaterToAirHeatPumpEquationFit'] = PydanticField(default='IB_CoilCoolingWaterToAirHeatPumpEquationFit')

__all__ = [
    'IB_CoilCoolingWaterToAirHeatPumpEquationFit',
]
