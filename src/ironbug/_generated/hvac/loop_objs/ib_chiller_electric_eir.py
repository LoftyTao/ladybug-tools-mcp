"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ChillerElectricEIR(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ChillerElectricEIR'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_ChillerElectricEIR.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_DualLoopObj',
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ChillerElectricEIR_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ReferenceCapacity',
        'ReferenceCOP',
        'ReferenceLeavingChilledWaterTemperature',
        'ReferenceEnteringCondenserFluidTemperature',
        'ReferenceChilledWaterFlowRate',
        'ReferenceCondenserFluidFlowRate',
        'CoolingCapacityFunctionOfTemperature',
        'ElectricInputToCoolingOutputRatioFunctionOfTemperature',
        'ElectricInputToCoolingOutputRatioFunctionOfPLR',
        'MinimumPartLoadRatio',
        'MaximumPartLoadRatio',
        'OptimumPartLoadRatio',
        'MinimumUnloadingRatio',
        'CondenserType',
        'CondenserFanPowerRatio',
        'FractionofCompressorElectricConsumptionRejectedbyCondenser',
        'LeavingChilledWaterLowerTemperatureLimit',
        'ChillerFlowMode',
        'DesignHeatRecoveryWaterFlowRate',
        'SizingFactor',
        'BasinHeaterCapacity',
        'BasinHeaterSetpointTemperature',
        'BasinHeaterSchedule',
        'CondenserHeatRecoveryRelativeCapacityFraction',
        'HeatRecoveryInletHighTemperatureLimitSchedule',
        'EndUseSubcategory',
        'CondenserFlowControl',
        'CondenserLoopFlowRateFractionFunctionofLoopPartLoadRatioCurve',
        'TemperatureDifferenceAcrossCondenserSchedule',
        'CondenserMinimumFlowFraction',
        'ThermosiphonCapacityFractionCurve',
        'ThermosiphonMinimumTemperatureDifference',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'BasinHeaterCapacity': 'float',
        'BasinHeaterSetpointTemperature': 'float',
        'ChillerFlowMode': 'str',
        'CondenserFanPowerRatio': 'float',
        'CondenserFlowControl': 'str',
        'CondenserHeatRecoveryRelativeCapacityFraction': 'float',
        'CondenserMinimumFlowFraction': 'float',
        'CondenserType': 'str',
        'CoolingCapacityFunctionOfTemperature': 'str | float | int | bool',
        'DesignHeatRecoveryWaterFlowRate': 'float',
        'ElectricInputToCoolingOutputRatioFunctionOfPLR': 'str | float | int | bool',
        'ElectricInputToCoolingOutputRatioFunctionOfTemperature': 'str | float | int | bool',
        'EndUseSubcategory': 'str',
        'FractionofCompressorElectricConsumptionRejectedbyCondenser': 'float',
        'LeavingChilledWaterLowerTemperatureLimit': 'float',
        'MaximumPartLoadRatio': 'float',
        'MinimumPartLoadRatio': 'float',
        'MinimumUnloadingRatio': 'float',
        'OptimumPartLoadRatio': 'float',
        'ReferenceCOP': 'float',
        'ReferenceCapacity': 'float',
        'ReferenceChilledWaterFlowRate': 'float',
        'ReferenceCondenserFluidFlowRate': 'float',
        'ReferenceEnteringCondenserFluidTemperature': 'float',
        'ReferenceLeavingChilledWaterTemperature': 'float',
        'SizingFactor': 'float',
        'ThermosiphonMinimumTemperatureDifference': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'BasinHeaterSchedule': 'IB_Schedule',
        'CondenserLoopFlowRateFractionFunctionofLoopPartLoadRatioCurve': 'IB_Curve',
        'HeatRecoveryInletHighTemperatureLimitSchedule': 'IB_Schedule',
        'TemperatureDifferenceAcrossCondenserSchedule': 'IB_Schedule',
        'ThermosiphonCapacityFractionCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ChillerElectricEIR'] = PydanticField(default='IB_ChillerElectricEIR')

__all__ = [
    'IB_ChillerElectricEIR',
]
