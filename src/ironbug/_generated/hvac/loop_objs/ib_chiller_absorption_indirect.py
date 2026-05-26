"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ChillerAbsorptionIndirect(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ChillerAbsorptionIndirect'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_ChillerAbsorptionIndirect.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_DualLoopObj',
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ChillerAbsorptionIndirect_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'NominalCapacity',
        'NominalPumpingPower',
        'MinimumPartLoadRatio',
        'MaximumPartLoadRatio',
        'OptimumPartLoadRatio',
        'DesignCondenserInletTemperature',
        'CondenserInletTemperatureLowerLimit',
        'ChilledWaterOutletTemperatureLowerLimit',
        'DesignChilledWaterFlowRate',
        'DesignCondenserWaterFlowRate',
        'ChillerFlowMode',
        'GeneratorHeatInputFunctionofPartLoadRatioCurve',
        'PumpElectricInputFunctionofPartLoadRatioCurve',
        'CapacityCorrectionFunctionofCondenserTemperatureCurve',
        'CapacityCorrectionFunctionofChilledWaterTemperatureCurve',
        'CapacityCorrectionFunctionofGeneratorTemperatureCurve',
        'GeneratorHeatInputCorrectionFunctionofCondenserTemperatureCurve',
        'GeneratorHeatInputCorrectionFunctionofChilledWaterTemperatureCurve',
        'GeneratorHeatSourceType',
        'DesignGeneratorFluidFlowRate',
        'TemperatureLowerLimitGeneratorInlet',
        'DegreeofSubcoolinginSteamGenerator',
        'DegreeofSubcoolinginSteamCondensateLoop',
        'SizingFactor',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ChilledWaterOutletTemperatureLowerLimit': 'float',
        'ChillerFlowMode': 'str',
        'CondenserInletTemperatureLowerLimit': 'float',
        'DegreeofSubcoolinginSteamCondensateLoop': 'float',
        'DegreeofSubcoolinginSteamGenerator': 'float',
        'DesignChilledWaterFlowRate': 'float',
        'DesignCondenserInletTemperature': 'float',
        'DesignCondenserWaterFlowRate': 'float',
        'DesignGeneratorFluidFlowRate': 'float',
        'GeneratorHeatSourceType': 'str',
        'MaximumPartLoadRatio': 'float',
        'MinimumPartLoadRatio': 'float',
        'NominalCapacity': 'float',
        'NominalPumpingPower': 'float',
        'OptimumPartLoadRatio': 'float',
        'SizingFactor': 'float',
        'TemperatureLowerLimitGeneratorInlet': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'CapacityCorrectionFunctionofChilledWaterTemperatureCurve': 'IB_Curve',
        'CapacityCorrectionFunctionofCondenserTemperatureCurve': 'IB_Curve',
        'CapacityCorrectionFunctionofGeneratorTemperatureCurve': 'IB_Curve',
        'GeneratorHeatInputCorrectionFunctionofChilledWaterTemperatureCurve': 'IB_Curve',
        'GeneratorHeatInputCorrectionFunctionofCondenserTemperatureCurve': 'IB_Curve',
        'GeneratorHeatInputFunctionofPartLoadRatioCurve': 'IB_Curve',
        'PumpElectricInputFunctionofPartLoadRatioCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ChillerAbsorptionIndirect'] = PydanticField(default='IB_ChillerAbsorptionIndirect')

__all__ = [
    'IB_ChillerAbsorptionIndirect',
]
