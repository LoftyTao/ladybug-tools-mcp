"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilHeatingWaterToAirHeatPumpEquationFit(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilHeatingWaterToAirHeatPumpEquationFit'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilHeatingWaterToAirHeatPumpEquationFit.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilHeatingBasic',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_DualLoopObj',
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilHeatingWaterToAirHeatPumpEquationFit_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'RatedAirFlowRate',
        'RatedWaterFlowRate',
        'RatedHeatingCapacity',
        'RatedHeatingCoefficientofPerformance',
        'RatedEnteringWaterTemperature',
        'RatedEnteringAirDryBulbTemperature',
        'RatioofRatedHeatingCapacitytoRatedCoolingCapacity',
        'HeatingCapacityCurve',
        'HeatingCapacityCoefficient1',
        'HeatingCapacityCoefficient2',
        'HeatingCapacityCoefficient3',
        'HeatingCapacityCoefficient4',
        'HeatingCapacityCoefficient5',
        'HeatingPowerConsumptionCurve',
        'HeatingPowerConsumptionCoefficient1',
        'HeatingPowerConsumptionCoefficient2',
        'HeatingPowerConsumptionCoefficient3',
        'HeatingPowerConsumptionCoefficient4',
        'HeatingPowerConsumptionCoefficient5',
        'PartLoadFractionCorrelationCurve',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'HeatingCapacityCoefficient1': 'str | float | int | bool',
        'HeatingCapacityCoefficient2': 'str | float | int | bool',
        'HeatingCapacityCoefficient3': 'str | float | int | bool',
        'HeatingCapacityCoefficient4': 'str | float | int | bool',
        'HeatingCapacityCoefficient5': 'str | float | int | bool',
        'HeatingPowerConsumptionCoefficient1': 'str | float | int | bool',
        'HeatingPowerConsumptionCoefficient2': 'str | float | int | bool',
        'HeatingPowerConsumptionCoefficient3': 'str | float | int | bool',
        'HeatingPowerConsumptionCoefficient4': 'str | float | int | bool',
        'HeatingPowerConsumptionCoefficient5': 'str | float | int | bool',
        'RatedAirFlowRate': 'float',
        'RatedEnteringAirDryBulbTemperature': 'float',
        'RatedEnteringWaterTemperature': 'float',
        'RatedHeatingCapacity': 'float',
        'RatedHeatingCoefficientofPerformance': 'float',
        'RatedWaterFlowRate': 'float',
        'RatioofRatedHeatingCapacitytoRatedCoolingCapacity': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'HeatingCapacityCurve': 'IB_Curve',
        'HeatingPowerConsumptionCurve': 'IB_Curve',
        'PartLoadFractionCorrelationCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilHeatingWaterToAirHeatPumpEquationFit'] = PydanticField(default='IB_CoilHeatingWaterToAirHeatPumpEquationFit')

__all__ = [
    'IB_CoilHeatingWaterToAirHeatPumpEquationFit',
]
