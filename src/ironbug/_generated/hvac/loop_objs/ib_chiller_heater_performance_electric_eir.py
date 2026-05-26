"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ChillerHeaterPerformanceElectricEIR(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ChillerHeaterPerformanceElectricEIR'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_ChillerHeaterPerformanceElectricEIR.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ModelObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ChillerHeaterPerformanceElectricEIR_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ReferenceCoolingModeEvaporatorCapacity',
        'ReferenceCoolingModeCOP',
        'ReferenceCoolingModeLeavingChilledWaterTemperature',
        'ReferenceCoolingModeEnteringCondenserFluidTemperature',
        'ReferenceCoolingModeLeavingCondenserWaterTemperature',
        'ReferenceHeatingModeCoolingCapacityRatio',
        'ReferenceHeatingModeCoolingPowerInputRatio',
        'ReferenceHeatingModeLeavingChilledWaterTemperature',
        'ReferenceHeatingModeLeavingCondenserWaterTemperature',
        'ReferenceHeatingModeEnteringCondenserFluidTemperature',
        'HeatingModeEnteringChilledWaterTemperatureLowLimit',
        'ChilledWaterFlowModeType',
        'DesignChilledWaterFlowRate',
        'DesignCondenserWaterFlowRate',
        'DesignHotWaterFlowRate',
        'CompressorMotorEfficiency',
        'CondenserType',
        'CoolingModeTemperatureCurveCondenserWaterIndependentVariable',
        'CoolingModeCoolingCapacityFunctionOfTemperatureCurve',
        'CoolingModeElectricInputToCoolingOutputRatioFunctionOfTemperatureCurve',
        'CoolingModeElectricInputToCoolingOutputRatioFunctionOfPartLoadRatioCurve',
        'CoolingModeCoolingCapacityOptimumPartLoadRatio',
        'HeatingModeTemperatureCurveCondenserWaterIndependentVariable',
        'HeatingModeCoolingCapacityFunctionOfTemperatureCurve',
        'HeatingModeElectricInputToCoolingOutputRatioFunctionOfTemperatureCurve',
        'HeatingModeElectricInputToCoolingOutputRatioFunctionOfPartLoadRatioCurve',
        'HeatingModeCoolingCapacityOptimumPartLoadRatio',
        'SizingFactor',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ChilledWaterFlowModeType': 'str',
        'CompressorMotorEfficiency': 'float',
        'CondenserType': 'str',
        'CoolingModeCoolingCapacityOptimumPartLoadRatio': 'float',
        'DesignChilledWaterFlowRate': 'float',
        'DesignCondenserWaterFlowRate': 'float',
        'DesignHotWaterFlowRate': 'float',
        'HeatingModeCoolingCapacityOptimumPartLoadRatio': 'float',
        'HeatingModeEnteringChilledWaterTemperatureLowLimit': 'float',
        'ReferenceCoolingModeCOP': 'float',
        'ReferenceCoolingModeEnteringCondenserFluidTemperature': 'float',
        'ReferenceCoolingModeEvaporatorCapacity': 'float',
        'ReferenceCoolingModeLeavingChilledWaterTemperature': 'float',
        'ReferenceCoolingModeLeavingCondenserWaterTemperature': 'float',
        'ReferenceHeatingModeCoolingCapacityRatio': 'float',
        'ReferenceHeatingModeCoolingPowerInputRatio': 'float',
        'ReferenceHeatingModeEnteringCondenserFluidTemperature': 'float',
        'ReferenceHeatingModeLeavingChilledWaterTemperature': 'float',
        'ReferenceHeatingModeLeavingCondenserWaterTemperature': 'float',
        'SizingFactor': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'CoolingModeCoolingCapacityFunctionOfTemperatureCurve': 'IB_Curve',
        'CoolingModeElectricInputToCoolingOutputRatioFunctionOfPartLoadRatioCurve': 'IB_Curve',
        'CoolingModeElectricInputToCoolingOutputRatioFunctionOfTemperatureCurve': 'IB_Curve',
        'CoolingModeTemperatureCurveCondenserWaterIndependentVariable': 'IB_Curve',
        'HeatingModeCoolingCapacityFunctionOfTemperatureCurve': 'IB_Curve',
        'HeatingModeElectricInputToCoolingOutputRatioFunctionOfPartLoadRatioCurve': 'IB_Curve',
        'HeatingModeElectricInputToCoolingOutputRatioFunctionOfTemperatureCurve': 'IB_Curve',
        'HeatingModeTemperatureCurveCondenserWaterIndependentVariable': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ChillerHeaterPerformanceElectricEIR'] = PydanticField(default='IB_ChillerHeaterPerformanceElectricEIR')

__all__ = [
    'IB_ChillerHeaterPerformanceElectricEIR',
]
