"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_HeatPumpWaterToWaterEquationFitCooling(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_HeatPumpWaterToWaterEquationFitCooling'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_HeatPumpWaterToWaterEquationFitCooling.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_DualLoopObj',
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_HeatPumpWaterToWaterEquationFitCooling_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ReferenceLoadSideFlowRate',
        'RatedLoadSideFlowRate',
        'ReferenceSourceSideFlowRate',
        'RatedSourceSideFlowRate',
        'RatedCoolingCapacity',
        'RatedCoolingPowerConsumption',
        'CoolingCapacityCurve',
        'CoolingCapacityCoefficient1',
        'CoolingCapacityCoefficient2',
        'CoolingCapacityCoefficient3',
        'CoolingCapacityCoefficient4',
        'CoolingCapacityCoefficient5',
        'CoolingCompressorPowerCurve',
        'CoolingCompressorPowerCoefficient1',
        'CoolingCompressorPowerCoefficient2',
        'CoolingCompressorPowerCoefficient3',
        'CoolingCompressorPowerCoefficient4',
        'CoolingCompressorPowerCoefficient5',
        'ReferenceCoefficientofPerformance',
        'SizingFactor',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CoolingCapacityCoefficient1': 'str | float | int | bool',
        'CoolingCapacityCoefficient2': 'str | float | int | bool',
        'CoolingCapacityCoefficient3': 'str | float | int | bool',
        'CoolingCapacityCoefficient4': 'str | float | int | bool',
        'CoolingCapacityCoefficient5': 'str | float | int | bool',
        'CoolingCompressorPowerCoefficient1': 'str | float | int | bool',
        'CoolingCompressorPowerCoefficient2': 'str | float | int | bool',
        'CoolingCompressorPowerCoefficient3': 'str | float | int | bool',
        'CoolingCompressorPowerCoefficient4': 'str | float | int | bool',
        'CoolingCompressorPowerCoefficient5': 'str | float | int | bool',
        'RatedCoolingCapacity': 'str | float | int | bool',
        'RatedCoolingPowerConsumption': 'str | float | int | bool',
        'RatedLoadSideFlowRate': 'str | float | int | bool',
        'RatedSourceSideFlowRate': 'str | float | int | bool',
        'ReferenceCoefficientofPerformance': 'float',
        'ReferenceLoadSideFlowRate': 'float',
        'ReferenceSourceSideFlowRate': 'float',
        'SizingFactor': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'CoolingCapacityCurve': 'IB_Curve',
        'CoolingCompressorPowerCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_HeatPumpWaterToWaterEquationFitCooling'] = PydanticField(default='IB_HeatPumpWaterToWaterEquationFitCooling')

__all__ = [
    'IB_HeatPumpWaterToWaterEquationFitCooling',
]
