"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_HeatPumpWaterToWaterEquationFitHeating(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_HeatPumpWaterToWaterEquationFitHeating'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_HeatPumpWaterToWaterEquationFitHeating.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_DualLoopObj',
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_HeatPumpWaterToWaterEquationFitHeating_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ReferenceLoadSideFlowRate',
        'RatedLoadSideFlowRate',
        'ReferenceSourceSideFlowRate',
        'RatedSourceSideFlowRate',
        'RatedHeatingCapacity',
        'RatedHeatingPowerConsumption',
        'HeatingCapacityCurve',
        'HeatingCapacityCoefficient1',
        'HeatingCapacityCoefficient2',
        'HeatingCapacityCoefficient3',
        'HeatingCapacityCoefficient4',
        'HeatingCapacityCoefficient5',
        'HeatingCompressorPowerCurve',
        'HeatingCompressorPowerCoefficient1',
        'HeatingCompressorPowerCoefficient2',
        'HeatingCompressorPowerCoefficient3',
        'HeatingCompressorPowerCoefficient4',
        'HeatingCompressorPowerCoefficient5',
        'ReferenceCoefficientofPerformance',
        'SizingFactor',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'HeatingCapacityCoefficient1': 'str | float | int | bool',
        'HeatingCapacityCoefficient2': 'str | float | int | bool',
        'HeatingCapacityCoefficient3': 'str | float | int | bool',
        'HeatingCapacityCoefficient4': 'str | float | int | bool',
        'HeatingCapacityCoefficient5': 'str | float | int | bool',
        'HeatingCompressorPowerCoefficient1': 'str | float | int | bool',
        'HeatingCompressorPowerCoefficient2': 'str | float | int | bool',
        'HeatingCompressorPowerCoefficient3': 'str | float | int | bool',
        'HeatingCompressorPowerCoefficient4': 'str | float | int | bool',
        'HeatingCompressorPowerCoefficient5': 'str | float | int | bool',
        'RatedHeatingCapacity': 'str | float | int | bool',
        'RatedHeatingPowerConsumption': 'str | float | int | bool',
        'RatedLoadSideFlowRate': 'str | float | int | bool',
        'RatedSourceSideFlowRate': 'str | float | int | bool',
        'ReferenceCoefficientofPerformance': 'float',
        'ReferenceLoadSideFlowRate': 'float',
        'ReferenceSourceSideFlowRate': 'float',
        'SizingFactor': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'HeatingCapacityCurve': 'IB_Curve',
        'HeatingCompressorPowerCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_HeatPumpWaterToWaterEquationFitHeating'] = PydanticField(default='IB_HeatPumpWaterToWaterEquationFitHeating')

__all__ = [
    'IB_HeatPumpWaterToWaterEquationFitHeating',
]
