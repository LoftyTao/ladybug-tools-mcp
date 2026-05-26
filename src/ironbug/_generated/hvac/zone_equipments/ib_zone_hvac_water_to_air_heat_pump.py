"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ZoneHVACWaterToAirHeatPump(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ZoneHVACWaterToAirHeatPump'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ZoneEquipments/ZoneHVAC/IB_ZoneHVACWaterToAirHeatPump.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ZoneEquipment',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ZoneHVACWaterToAirHeatPump_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'SupplyAirFlowRateDuringCoolingOperation',
        'SupplyAirFlowRateDuringHeatingOperation',
        'SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded',
        'NoLoadSupplyAirFlowRateControlSetToLowSpeed',
        'OutdoorAirFlowRateDuringCoolingOperation',
        'OutdoorAirFlowRateDuringHeatingOperation',
        'OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded',
        'MaximumCyclingRate',
        'HeatPumpTimeConstant',
        'FractionofOnCyclePowerUse',
        'HeatPumpFanDelayTime',
        'MaximumSupplyAirTemperaturefromSupplementalHeater',
        'MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation',
        'FanPlacement',
        'HeatPumpCoilWaterFlowMode',
        'SupplyAirFanOperatingModeSchedule',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'FanPlacement': 'str',
        'FractionofOnCyclePowerUse': 'str | float | int | bool',
        'HeatPumpCoilWaterFlowMode': 'str',
        'HeatPumpFanDelayTime': 'str | float | int | bool',
        'HeatPumpTimeConstant': 'str | float | int | bool',
        'MaximumCyclingRate': 'str | float | int | bool',
        'MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation': 'float',
        'MaximumSupplyAirTemperaturefromSupplementalHeater': 'float',
        'NoLoadSupplyAirFlowRateControlSetToLowSpeed': 'bool | str',
        'OutdoorAirFlowRateDuringCoolingOperation': 'float',
        'OutdoorAirFlowRateDuringHeatingOperation': 'float',
        'OutdoorAirFlowRateWhenNoCoolingorHeatingisNeeded': 'float',
        'SupplyAirFlowRateDuringCoolingOperation': 'float',
        'SupplyAirFlowRateDuringHeatingOperation': 'float',
        'SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'SupplyAirFanOperatingModeSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ZoneHVACWaterToAirHeatPump'] = PydanticField(default='IB_ZoneHVACWaterToAirHeatPump')

__all__ = [
    'IB_ZoneHVACWaterToAirHeatPump',
]
