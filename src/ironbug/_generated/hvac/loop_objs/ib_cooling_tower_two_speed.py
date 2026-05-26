"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoolingTowerTwoSpeed(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoolingTowerTwoSpeed'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoolingTowerTwoSpeed.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_PlantLoopObjects',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoolingTowerTwoSpeed_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'DesignWaterFlowRate',
        'HighFanSpeedAirFlowRate',
        'HighFanSpeedFanPower',
        'HighFanSpeedUFactorTimesAreaValue',
        'LowFanSpeedAirFlowRate',
        'LowFanSpeedAirFlowRateSizingFactor',
        'LowFanSpeedFanPower',
        'LowFanSpeedFanPowerSizingFactor',
        'LowFanSpeedUFactorTimesAreaValue',
        'LowFanSpeedUFactorTimesAreaSizingFactor',
        'FreeConvectionRegimeAirFlowRate',
        'FreeConvectionRegimeAirFlowRateSizingFactor',
        'FreeConvectionRegimeUFactorTimesAreaValue',
        'FreeConvectionUFactorTimesAreaValueSizingFactor',
        'PerformanceInputMethod',
        'HeatRejectionCapacityandNominalCapacitySizingRatio',
        'HighSpeedNominalCapacity',
        'LowSpeedNominalCapacity',
        'LowSpeedNominalCapacitySizingFactor',
        'FreeConvectionNominalCapacity',
        'FreeConvectionNominalCapacitySizingFactor',
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
        'DesignInletAirDryBulbTemperature',
        'DesignInletAirWetBulbTemperature',
        'DesignApproachTemperature',
        'DesignRangeTemperature',
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
        'DesignApproachTemperature': 'float',
        'DesignInletAirDryBulbTemperature': 'float',
        'DesignInletAirWetBulbTemperature': 'float',
        'DesignRangeTemperature': 'float',
        'DesignWaterFlowRate': 'float',
        'DriftLossPercent': 'float',
        'EndUseSubcategory': 'str',
        'EvaporationLossFactor': 'float',
        'EvaporationLossMode': 'str',
        'FreeConvectionNominalCapacity': 'float',
        'FreeConvectionNominalCapacitySizingFactor': 'float',
        'FreeConvectionRegimeAirFlowRate': 'float',
        'FreeConvectionRegimeAirFlowRateSizingFactor': 'float',
        'FreeConvectionRegimeUFactorTimesAreaValue': 'float',
        'FreeConvectionUFactorTimesAreaValueSizingFactor': 'float',
        'HeatRejectionCapacityandNominalCapacitySizingRatio': 'float',
        'HighFanSpeedAirFlowRate': 'float',
        'HighFanSpeedFanPower': 'float',
        'HighFanSpeedUFactorTimesAreaValue': 'float',
        'HighSpeedNominalCapacity': 'float',
        'LowFanSpeedAirFlowRate': 'float',
        'LowFanSpeedAirFlowRateSizingFactor': 'float',
        'LowFanSpeedFanPower': 'float',
        'LowFanSpeedFanPowerSizingFactor': 'float',
        'LowFanSpeedUFactorTimesAreaSizingFactor': 'float',
        'LowFanSpeedUFactorTimesAreaValue': 'float',
        'LowSpeedNominalCapacity': 'float',
        'LowSpeedNominalCapacitySizingFactor': 'float',
        'NumberofCells': 'int',
        'PerformanceInputMethod': 'str',
        'SizingFactor': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'BasinHeaterOperatingSchedule': 'IB_Schedule',
        'BlowdownMakeupWaterUsageSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoolingTowerTwoSpeed'] = PydanticField(default='IB_CoolingTowerTwoSpeed')

__all__ = [
    'IB_CoolingTowerTwoSpeed',
]
