"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_CoilCoolingDXTwoSpeed(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_CoilCoolingDXTwoSpeed'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_CoilCoolingDXTwoSpeed.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_CoilDX',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_CoilCoolingDXTwoSpeed_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'RatedHighSpeedTotalCoolingCapacity',
        'RatedHighSpeedSensibleHeatRatio',
        'RatedHighSpeedCOP',
        'RatedHighSpeedAirFlowRate',
        'RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2017',
        'RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2023',
        'TotalCoolingCapacityFunctionOfTemperatureCurve',
        'TotalCoolingCapacityFunctionOfFlowFractionCurve',
        'EnergyInputRatioFunctionOfTemperatureCurve',
        'EnergyInputRatioFunctionOfFlowFractionCurve',
        'PartLoadFractionCorrelationCurve',
        'RatedLowSpeedTotalCoolingCapacity',
        'RatedLowSpeedSensibleHeatRatio',
        'RatedLowSpeedCOP',
        'RatedLowSpeedAirFlowRate',
        'RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2017',
        'RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2023',
        'LowSpeedTotalCoolingCapacityFunctionOfTemperatureCurve',
        'LowSpeedEnergyInputRatioFunctionOfTemperatureCurve',
        'CondenserType',
        'HighSpeedEvaporativeCondenserEffectiveness',
        'HighSpeedEvaporativeCondenserAirFlowRate',
        'HighSpeedEvaporativeCondenserPumpRatedPowerConsumption',
        'LowSpeedEvaporativeCondenserEffectiveness',
        'LowSpeedEvaporativeCondenserAirFlowRate',
        'LowSpeedEvaporativeCondenserPumpRatedPowerConsumption',
        'BasinHeaterCapacity',
        'BasinHeaterSetpointTemperature',
        'BasinHeaterOperatingSchedule',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation',
        'UnitInternalStaticAirPressure',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'BasinHeaterCapacity': 'float',
        'BasinHeaterSetpointTemperature': 'float',
        'CondenserType': 'str',
        'HighSpeedEvaporativeCondenserAirFlowRate': 'float',
        'HighSpeedEvaporativeCondenserEffectiveness': 'float',
        'HighSpeedEvaporativeCondenserPumpRatedPowerConsumption': 'float',
        'LowSpeedEvaporativeCondenserAirFlowRate': 'float',
        'LowSpeedEvaporativeCondenserEffectiveness': 'float',
        'LowSpeedEvaporativeCondenserPumpRatedPowerConsumption': 'float',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation': 'float',
        'RatedHighSpeedAirFlowRate': 'float',
        'RatedHighSpeedCOP': 'float',
        'RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2017': 'float',
        'RatedHighSpeedEvaporatorFanPowerPerVolumeFlowRate2023': 'float',
        'RatedHighSpeedSensibleHeatRatio': 'float',
        'RatedHighSpeedTotalCoolingCapacity': 'float',
        'RatedLowSpeedAirFlowRate': 'float',
        'RatedLowSpeedCOP': 'float',
        'RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2017': 'float',
        'RatedLowSpeedEvaporatorFanPowerPerVolumeFlowRate2023': 'float',
        'RatedLowSpeedSensibleHeatRatio': 'float',
        'RatedLowSpeedTotalCoolingCapacity': 'float',
        'UnitInternalStaticAirPressure': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'BasinHeaterOperatingSchedule': 'IB_Schedule',
        'EnergyInputRatioFunctionOfFlowFractionCurve': 'IB_Curve',
        'EnergyInputRatioFunctionOfTemperatureCurve': 'IB_Curve',
        'LowSpeedEnergyInputRatioFunctionOfTemperatureCurve': 'IB_Curve',
        'LowSpeedTotalCoolingCapacityFunctionOfTemperatureCurve': 'IB_Curve',
        'PartLoadFractionCorrelationCurve': 'IB_Curve',
        'TotalCoolingCapacityFunctionOfFlowFractionCurve': 'IB_Curve',
        'TotalCoolingCapacityFunctionOfTemperatureCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_CoilCoolingDXTwoSpeed'] = PydanticField(default='IB_CoilCoolingDXTwoSpeed')

__all__ = [
    'IB_CoilCoolingDXTwoSpeed',
]
