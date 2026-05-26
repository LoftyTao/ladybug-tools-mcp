"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_HeatPumpPlantLoopEIRHeating(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_HeatPumpPlantLoopEIRHeating'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_HeatPumpPlantLoopEIRHeating.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_PlantLoopObjects',
        'IIB_DualLoopObj',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_HeatPumpPlantLoopEIRHeating_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'CondenserType',
        'LoadSideReferenceFlowRate',
        'SourceSideReferenceFlowRate',
        'HeatRecoveryReferenceFlowRate',
        'ReferenceCapacity',
        'ReferenceCoefficientofPerformance',
        'SizingFactor',
        'CapacityModifierFunctionofTemperatureCurve',
        'ElectricInputtoOutputRatioModifierFunctionofTemperatureCurve',
        'ElectricInputtoOutputRatioModifierFunctionofPartLoadRatioCurve',
        'HeatingToCoolingCapacitySizingRatio',
        'HeatPumpSizingMethod',
        'ControlType',
        'FlowMode',
        'MinimumPartLoadRatio',
        'MinimumSourceInletTemperature',
        'MaximumSourceInletTemperature',
        'MinimumSupplyWaterTemperatureCurve',
        'MaximumSupplyWaterTemperatureCurve',
        'DryOutdoorCorrectionFactorCurve',
        'MaximumOutdoorDryBulbTemperatureForDefrostOperation',
        'HeatPumpDefrostControl',
        'HeatPumpDefrostTimePeriodFraction',
        'DefrostEnergyInputRatioFunctionofTemperatureCurve',
        'TimedEmpiricalDefrostFrequencyCurve',
        'TimedEmpiricalDefrostHeatLoadPenaltyCurve',
        'TimedEmpiricalDefrostHeatInputEnergyFractionCurve',
        'MinimumHeatRecoveryOutletTemperature',
        'HeatRecoveryCapacityModifierFunctionofTemperatureCurve',
        'HeatRecoveryElectricInputtoOutputRatioModifierFunctionofTemperatureCurve',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CondenserType': 'str',
        'ControlType': 'str',
        'FlowMode': 'str',
        'HeatPumpDefrostControl': 'str',
        'HeatPumpDefrostTimePeriodFraction': 'float',
        'HeatPumpSizingMethod': 'str',
        'HeatRecoveryReferenceFlowRate': 'float',
        'HeatingToCoolingCapacitySizingRatio': 'float',
        'LoadSideReferenceFlowRate': 'float',
        'MaximumOutdoorDryBulbTemperatureForDefrostOperation': 'float',
        'MaximumSourceInletTemperature': 'float',
        'MinimumHeatRecoveryOutletTemperature': 'float',
        'MinimumPartLoadRatio': 'float',
        'MinimumSourceInletTemperature': 'float',
        'ReferenceCapacity': 'float',
        'ReferenceCoefficientofPerformance': 'float',
        'SizingFactor': 'float',
        'SourceSideReferenceFlowRate': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'CapacityModifierFunctionofTemperatureCurve': 'IB_Curve',
        'DefrostEnergyInputRatioFunctionofTemperatureCurve': 'IB_Curve',
        'DryOutdoorCorrectionFactorCurve': 'IB_Curve',
        'ElectricInputtoOutputRatioModifierFunctionofPartLoadRatioCurve': 'IB_Curve',
        'ElectricInputtoOutputRatioModifierFunctionofTemperatureCurve': 'IB_Curve',
        'HeatRecoveryCapacityModifierFunctionofTemperatureCurve': 'IB_Curve',
        'HeatRecoveryElectricInputtoOutputRatioModifierFunctionofTemperatureCurve': 'IB_Curve',
        'MaximumSupplyWaterTemperatureCurve': 'IB_Curve',
        'MinimumSupplyWaterTemperatureCurve': 'IB_Curve',
        'TimedEmpiricalDefrostFrequencyCurve': 'IB_Curve',
        'TimedEmpiricalDefrostHeatInputEnergyFractionCurve': 'IB_Curve',
        'TimedEmpiricalDefrostHeatLoadPenaltyCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_HeatPumpPlantLoopEIRHeating'] = PydanticField(default='IB_HeatPumpPlantLoopEIRHeating')

__all__ = [
    'IB_HeatPumpPlantLoopEIRHeating',
]
