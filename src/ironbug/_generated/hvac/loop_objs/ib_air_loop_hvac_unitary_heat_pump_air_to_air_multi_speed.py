"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_AirLoopHVACUnitary',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'SupplyAirFanPlacement',
        'SupplyAirFanOperatingModeSchedule',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation',
        'MaximumSupplyAirTemperaturefromSupplementalHeater',
        'MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation',
        'AuxiliaryOnCycleElectricPower',
        'AuxiliaryOffCycleElectricPower',
        'DesignHeatRecoveryWaterFlowRate',
        'MaximumTemperatureforHeatRecovery',
        'SupplyAirFlowRateWhenNoCoolingorHeatingisNeeded',
        'NumberofSpeedsforHeating',
        'NumberofSpeedsforCooling',
        'Speed1SupplyAirFlowRateDuringHeatingOperation',
        'Speed2SupplyAirFlowRateDuringHeatingOperation',
        'Speed3SupplyAirFlowRateDuringHeatingOperation',
        'Speed4SupplyAirFlowRateDuringHeatingOperation',
        'Speed1SupplyAirFlowRateDuringCoolingOperation',
        'Speed2SupplyAirFlowRateDuringCoolingOperation',
        'Speed3SupplyAirFlowRateDuringCoolingOperation',
        'Speed4SupplyAirFlowRateDuringCoolingOperation',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'AuxiliaryOffCycleElectricPower': 'float',
        'AuxiliaryOnCycleElectricPower': 'float',
        'DesignHeatRecoveryWaterFlowRate': 'float',
        'MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation': 'float',
        'MaximumSupplyAirTemperaturefromSupplementalHeater': 'float',
        'MaximumTemperatureforHeatRecovery': 'float',
        'MinimumOutdoorDryBulbTemperatureforCompressorOperation': 'float',
        'NumberofSpeedsforCooling': 'int',
        'NumberofSpeedsforHeating': 'int',
        'Speed1SupplyAirFlowRateDuringCoolingOperation': 'float',
        'Speed1SupplyAirFlowRateDuringHeatingOperation': 'float',
        'Speed2SupplyAirFlowRateDuringCoolingOperation': 'float',
        'Speed2SupplyAirFlowRateDuringHeatingOperation': 'float',
        'Speed3SupplyAirFlowRateDuringCoolingOperation': 'float',
        'Speed3SupplyAirFlowRateDuringHeatingOperation': 'float',
        'Speed4SupplyAirFlowRateDuringCoolingOperation': 'float',
        'Speed4SupplyAirFlowRateDuringHeatingOperation': 'float',
        'SupplyAirFanPlacement': 'str',
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
    type: Literal['IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed'] = PydanticField(default='IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed')

__all__ = [
    'IB_AirLoopHVACUnitaryHeatPumpAirToAirMultiSpeed',
]
