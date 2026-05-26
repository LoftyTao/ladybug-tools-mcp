"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_AirLoopHVACUnitarySystem(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_AirLoopHVACUnitarySystem'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_AirLoopHVACUnitarySystem.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_AirLoopHVACUnitary',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_ZoneEquipment',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_AirLoopHVACUnitarySystem_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ControlType',
        'DehumidificationControlType',
        'AvailabilitySchedule',
        'FanPlacement',
        'SupplyAirFanOperatingModeSchedule',
        'DXHeatingCoilSizingRatio',
        'UseDOASDXCoolingCoil',
        'DOASDXCoolingCoilLeavingMinimumAirTemperature',
        'LatentLoadControl',
        'SupplyAirFlowRateDuringCoolingOperation',
        'SupplyAirFlowRatePerFloorAreaDuringCoolingOperation',
        'FractionofAutosizedDesignCoolingSupplyAirFlowRate',
        'DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperation',
        'SupplyAirFlowRateMethodDuringCoolingOperation',
        'SupplyAirFlowRateDuringHeatingOperation',
        'SupplyAirFlowRatePerFloorAreaduringHeatingOperation',
        'FractionofAutosizedDesignHeatingSupplyAirFlowRate',
        'DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperation',
        'SupplyAirFlowRateMethodDuringHeatingOperation',
        'SupplyAirFlowRateWhenNoCoolingorHeatingisRequired',
        'SupplyAirFlowRatePerFloorAreaWhenNoCoolingorHeatingisRequired',
        'FractionofAutosizedDesignCoolingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired',
        'FractionofAutosizedDesignHeatingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired',
        'DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperationWhenNoCoolingorHeatingisRequired',
        'DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperationWhenNoCoolingorHeatingisRequired',
        'NoLoadSupplyAirFlowRateControlSetToLowSpeed',
        'SupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired',
        'MaximumSupplyAirTemperature',
        'MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation',
        'MaximumCyclingRate',
        'HeatPumpTimeConstant',
        'FractionofOnCyclePowerUse',
        'HeatPumpFanDelayTime',
        'AncilliaryOnCycleElectricPower',
        'AncilliaryOffCycleElectricPower',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'AncilliaryOffCycleElectricPower': 'float',
        'AncilliaryOnCycleElectricPower': 'float',
        'ControlType': 'str',
        'DOASDXCoolingCoilLeavingMinimumAirTemperature': 'float',
        'DXHeatingCoilSizingRatio': 'float',
        'DehumidificationControlType': 'str',
        'DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperation': 'float',
        'DesignSupplyAirFlowRatePerUnitofCapacityDuringCoolingOperationWhenNoCoolingorHeatingisRequired': 'float',
        'DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperation': 'float',
        'DesignSupplyAirFlowRatePerUnitofCapacityDuringHeatingOperationWhenNoCoolingorHeatingisRequired': 'float',
        'FanPlacement': 'str',
        'FractionofAutosizedDesignCoolingSupplyAirFlowRate': 'float',
        'FractionofAutosizedDesignCoolingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired': 'float',
        'FractionofAutosizedDesignHeatingSupplyAirFlowRate': 'float',
        'FractionofAutosizedDesignHeatingSupplyAirFlowRateWhenNoCoolingorHeatingisRequired': 'float',
        'FractionofOnCyclePowerUse': 'str | float | int | bool',
        'HeatPumpFanDelayTime': 'str | float | int | bool',
        'HeatPumpTimeConstant': 'str | float | int | bool',
        'LatentLoadControl': 'str',
        'MaximumCyclingRate': 'str | float | int | bool',
        'MaximumOutdoorDryBulbTemperatureforSupplementalHeaterOperation': 'float',
        'MaximumSupplyAirTemperature': 'float',
        'NoLoadSupplyAirFlowRateControlSetToLowSpeed': 'bool | str',
        'SupplyAirFlowRateDuringCoolingOperation': 'float',
        'SupplyAirFlowRateDuringHeatingOperation': 'float',
        'SupplyAirFlowRateMethodDuringCoolingOperation': 'str',
        'SupplyAirFlowRateMethodDuringHeatingOperation': 'str',
        'SupplyAirFlowRateMethodWhenNoCoolingorHeatingisRequired': 'str',
        'SupplyAirFlowRatePerFloorAreaDuringCoolingOperation': 'float',
        'SupplyAirFlowRatePerFloorAreaWhenNoCoolingorHeatingisRequired': 'float',
        'SupplyAirFlowRatePerFloorAreaduringHeatingOperation': 'float',
        'SupplyAirFlowRateWhenNoCoolingorHeatingisRequired': 'float',
        'UseDOASDXCoolingCoil': 'bool | str',
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
    type: Literal['IB_AirLoopHVACUnitarySystem'] = PydanticField(default='IB_AirLoopHVACUnitarySystem')

__all__ = [
    'IB_AirLoopHVACUnitarySystem',
]
