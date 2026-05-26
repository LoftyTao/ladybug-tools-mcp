"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoolingTowerVariableSpeed(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoolingTowerVariableSpeed'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoolingTowerVariableSpeed.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoolingTowerVariableSpeed_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ModelType',
        'DesignInletAirWetBulbTemperature',
        'DesignApproachTemperature',
        'DesignRangeTemperature',
        'DesignWaterFlowRate',
        'DesignAirFlowRate',
        'DesignFanPower',
        'FanPowerRatioFunctionofAirFlowRateRatioCurve',
        'MinimumAirFlowRateRatio',
        'FractionofTowerCapacityinFreeConvectionRegime',
        'BasinHeaterCapacity',
        'BasinHeaterSetpointTemperature',
        'BasinHeaterOperatingSchedule',
        'EvaporationLossMode',
        'EvaporationLossFactor',
        'DriftLossPercent',
        'BlowdownCalculationMode',
        'BlowdownConcentrationRatio',
        'BlowdownMakeupWaterUsageSchedule',
        'NumberofCells',
        'CellControl',
        'CellMinimumWaterFlowRateFraction',
        'CellMaximumWaterFlowRateFraction',
        'SizingFactor',
        'EndUseSubcategory',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'BasinHeaterCapacity': 'float',
        'BasinHeaterSetpointTemperature': 'float',
        'BlowdownCalculationMode': 'str',
        'BlowdownConcentrationRatio': 'float',
        'CellControl': 'str',
        'CellMaximumWaterFlowRateFraction': 'float',
        'CellMinimumWaterFlowRateFraction': 'float',
        'DesignAirFlowRate': 'float',
        'DesignApproachTemperature': 'float',
        'DesignFanPower': 'float',
        'DesignInletAirWetBulbTemperature': 'float',
        'DesignRangeTemperature': 'float',
        'DesignWaterFlowRate': 'float',
        'DriftLossPercent': 'float',
        'EndUseSubcategory': 'str',
        'EvaporationLossFactor': 'float',
        'EvaporationLossMode': 'str',
        'FractionofTowerCapacityinFreeConvectionRegime': 'float',
        'MinimumAirFlowRateRatio': 'float',
        'ModelType': 'str',
        'NumberofCells': 'int',
        'SizingFactor': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'BasinHeaterOperatingSchedule': 'IB_Schedule',
        'BlowdownMakeupWaterUsageSchedule': 'IB_Schedule',
        'FanPowerRatioFunctionofAirFlowRateRatioCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoolingTowerVariableSpeed'] = PydanticField(default='IB_CoolingTowerVariableSpeed')

__all__ = [
    'IB_CoolingTowerVariableSpeed',
]
