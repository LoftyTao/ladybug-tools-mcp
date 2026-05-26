"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_SizingZone(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_SizingZone'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_SizingZone.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ModelObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_SizingZone_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'ZoneCoolingDesignSupplyAirTemperatureInputMethod',
        'ZoneCoolingDesignSupplyAirTemperature',
        'ZoneCoolingDesignSupplyAirTemperatureDifference',
        'ZoneHeatingDesignSupplyAirTemperatureInputMethod',
        'ZoneHeatingDesignSupplyAirTemperature',
        'ZoneHeatingDesignSupplyAirTemperatureDifference',
        'ZoneCoolingDesignSupplyAirHumidityRatio',
        'ZoneHeatingDesignSupplyAirHumidityRatio',
        'ZoneHeatingSizingFactor',
        'ZoneCoolingSizingFactor',
        'CoolingDesignAirFlowMethod',
        'CoolingDesignAirFlowRate',
        'CoolingMinimumAirFlowperZoneFloorArea',
        'CoolingMinimumAirFlow',
        'CoolingMinimumAirFlowFraction',
        'HeatingDesignAirFlowMethod',
        'HeatingDesignAirFlowRate',
        'HeatingMaximumAirFlowperZoneFloorArea',
        'HeatingMaximumAirFlow',
        'HeatingMaximumAirFlowFraction',
        'AccountforDedicatedOutdoorAirSystem',
        'DedicatedOutdoorAirSystemControlStrategy',
        'DedicatedOutdoorAirLowSetpointTemperatureforDesign',
        'DedicatedOutdoorAirHighSetpointTemperatureforDesign',
        'ZoneLoadSizingMethod',
        'ZoneLatentCoolingDesignSupplyAirHumidityRatioInputMethod',
        'ZoneDehumidificationDesignSupplyAirHumidityRatio',
        'ZoneCoolingDesignSupplyAirHumidityRatioDifference',
        'ZoneLatentHeatingDesignSupplyAirHumidityRatioInputMethod',
        'ZoneHumidificationDesignSupplyAirHumidityRatio',
        'ZoneHumidificationDesignSupplyAirHumidityRatioDifference',
        'ZoneHumidistatDehumidificationSetPointSchedule',
        'ZoneHumidistatHumidificationSetPointSchedule',
        'DesignZoneAirDistributionEffectivenessinCoolingMode',
        'DesignZoneAirDistributionEffectivenessinHeatingMode',
        'DesignZoneSecondaryRecirculationFraction',
        'DesignMinimumZoneVentilationEfficiency',
        'SizingOption',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'AccountforDedicatedOutdoorAirSystem': 'bool | str',
        'CoolingDesignAirFlowMethod': 'str',
        'CoolingDesignAirFlowRate': 'float',
        'CoolingMinimumAirFlow': 'float',
        'CoolingMinimumAirFlowFraction': 'float',
        'CoolingMinimumAirFlowperZoneFloorArea': 'float',
        'DedicatedOutdoorAirHighSetpointTemperatureforDesign': 'float',
        'DedicatedOutdoorAirLowSetpointTemperatureforDesign': 'float',
        'DedicatedOutdoorAirSystemControlStrategy': 'str',
        'DesignMinimumZoneVentilationEfficiency': 'float',
        'DesignZoneAirDistributionEffectivenessinCoolingMode': 'float',
        'DesignZoneAirDistributionEffectivenessinHeatingMode': 'float',
        'DesignZoneSecondaryRecirculationFraction': 'float',
        'HeatingDesignAirFlowMethod': 'str',
        'HeatingDesignAirFlowRate': 'float',
        'HeatingMaximumAirFlow': 'float',
        'HeatingMaximumAirFlowFraction': 'float',
        'HeatingMaximumAirFlowperZoneFloorArea': 'float',
        'SizingOption': 'str',
        'ZoneCoolingDesignSupplyAirHumidityRatio': 'float',
        'ZoneCoolingDesignSupplyAirHumidityRatioDifference': 'float',
        'ZoneCoolingDesignSupplyAirTemperature': 'float',
        'ZoneCoolingDesignSupplyAirTemperatureDifference': 'float',
        'ZoneCoolingDesignSupplyAirTemperatureInputMethod': 'str',
        'ZoneCoolingSizingFactor': 'float',
        'ZoneDehumidificationDesignSupplyAirHumidityRatio': 'float',
        'ZoneHeatingDesignSupplyAirHumidityRatio': 'float',
        'ZoneHeatingDesignSupplyAirTemperature': 'float',
        'ZoneHeatingDesignSupplyAirTemperatureDifference': 'float',
        'ZoneHeatingDesignSupplyAirTemperatureInputMethod': 'str',
        'ZoneHeatingSizingFactor': 'float',
        'ZoneHumidificationDesignSupplyAirHumidityRatio': 'float',
        'ZoneHumidificationDesignSupplyAirHumidityRatioDifference': 'float',
        'ZoneLatentCoolingDesignSupplyAirHumidityRatioInputMethod': 'str',
        'ZoneLatentHeatingDesignSupplyAirHumidityRatioInputMethod': 'str',
        'ZoneLoadSizingMethod': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'ZoneHumidistatDehumidificationSetPointSchedule': 'IB_Schedule',
        'ZoneHumidistatHumidificationSetPointSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_SizingZone'] = PydanticField(default='IB_SizingZone')

__all__ = [
    'IB_SizingZone',
]
