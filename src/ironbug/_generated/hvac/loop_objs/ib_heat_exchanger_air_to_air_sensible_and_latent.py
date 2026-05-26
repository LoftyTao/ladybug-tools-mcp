"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_HeatExchangerAirToAirSensibleAndLatent(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_HeatExchangerAirToAirSensibleAndLatent'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_HeatExchangerAirToAirSensibleAndLatent.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_AirLoopObject',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_HeatExchangerAirToAirSensibleAndLatent_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'NominalSupplyAirFlowRate',
        'SensibleEffectivenessat100HeatingAirFlow',
        'LatentEffectivenessat100HeatingAirFlow',
        'SensibleEffectivenessat75HeatingAirFlow',
        'LatentEffectivenessat75HeatingAirFlow',
        'SensibleEffectivenessat100CoolingAirFlow',
        'LatentEffectivenessat100CoolingAirFlow',
        'SensibleEffectivenessat75CoolingAirFlow',
        'LatentEffectivenessat75CoolingAirFlow',
        'NominalElectricPower',
        'SupplyAirOutletTemperatureControl',
        'HeatExchangerType',
        'FrostControlType',
        'ThresholdTemperature',
        'InitialDefrostTimeFraction',
        'RateofDefrostTimeFractionIncrease',
        'EconomizerLockout',
        'SensibleEffectivenessofHeatingAirFlowCurve',
        'LatentEffectivenessofHeatingAirFlowCurve',
        'SensibleEffectivenessofCoolingAirFlowCurve',
        'LatentEffectivenessofCoolingAirFlowCurve',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'EconomizerLockout': 'bool | str',
        'FrostControlType': 'str',
        'HeatExchangerType': 'str',
        'InitialDefrostTimeFraction': 'float',
        'LatentEffectivenessat100CoolingAirFlow': 'float',
        'LatentEffectivenessat100HeatingAirFlow': 'float',
        'LatentEffectivenessat75CoolingAirFlow': 'str | float | int | bool',
        'LatentEffectivenessat75HeatingAirFlow': 'str | float | int | bool',
        'NominalElectricPower': 'float',
        'NominalSupplyAirFlowRate': 'float',
        'RateofDefrostTimeFractionIncrease': 'float',
        'SensibleEffectivenessat100CoolingAirFlow': 'float',
        'SensibleEffectivenessat100HeatingAirFlow': 'float',
        'SensibleEffectivenessat75CoolingAirFlow': 'str | float | int | bool',
        'SensibleEffectivenessat75HeatingAirFlow': 'str | float | int | bool',
        'SupplyAirOutletTemperatureControl': 'bool | str',
        'ThresholdTemperature': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'LatentEffectivenessofCoolingAirFlowCurve': 'IB_Curve',
        'LatentEffectivenessofHeatingAirFlowCurve': 'IB_Curve',
        'SensibleEffectivenessofCoolingAirFlowCurve': 'IB_Curve',
        'SensibleEffectivenessofHeatingAirFlowCurve': 'IB_Curve',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_HeatExchangerAirToAirSensibleAndLatent'] = PydanticField(default='IB_HeatExchangerAirToAirSensibleAndLatent')

__all__ = [
    'IB_HeatExchangerAirToAirSensibleAndLatent',
]
