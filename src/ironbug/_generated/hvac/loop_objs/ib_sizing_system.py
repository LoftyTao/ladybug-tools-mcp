"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_SizingSystem(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_SizingSystem'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_SizingSystem.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ModelObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_SizingSystem_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'TypeofLoadtoSizeOn',
        'DesignOutdoorAirFlowRate',
        'CentralHeatingMaximumSystemAirFlowRatio',
        'PreheatDesignTemperature',
        'PreheatDesignHumidityRatio',
        'PrecoolDesignTemperature',
        'PrecoolDesignHumidityRatio',
        'CentralCoolingDesignSupplyAirTemperature',
        'CentralHeatingDesignSupplyAirTemperature',
        'SizingOption',
        'AllOutdoorAirinCooling',
        'AllOutdoorAirinHeating',
        'CentralCoolingDesignSupplyAirHumidityRatio',
        'CentralHeatingDesignSupplyAirHumidityRatio',
        'CoolingDesignAirFlowMethod',
        'CoolingDesignAirFlowRate',
        'HeatingDesignAirFlowMethod',
        'HeatingDesignAirFlowRate',
        'SystemOutdoorAirMethod',
        'ZoneMaximumOutdoorAirFraction',
        'CoolingSupplyAirFlowRatePerFloorArea',
        'CoolingFractionofAutosizedCoolingSupplyAirFlowRate',
        'CoolingSupplyAirFlowRatePerUnitCoolingCapacity',
        'HeatingSupplyAirFlowRatePerFloorArea',
        'HeatingFractionofAutosizedHeatingSupplyAirFlowRate',
        'HeatingFractionofAutosizedCoolingSupplyAirFlowRate',
        'HeatingSupplyAirFlowRatePerUnitHeatingCapacity',
        'CoolingDesignCapacityMethod',
        'CoolingDesignCapacity',
        'CoolingDesignCapacityPerFloorArea',
        'FractionofAutosizedCoolingDesignCapacity',
        'HeatingDesignCapacityMethod',
        'HeatingDesignCapacity',
        'HeatingDesignCapacityPerFloorArea',
        'FractionofAutosizedHeatingDesignCapacity',
        'CentralCoolingCapacityControlMethod',
        'OccupantDiversity',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'AllOutdoorAirinCooling': 'str | float | int | bool',
        'AllOutdoorAirinHeating': 'str | float | int | bool',
        'CentralCoolingCapacityControlMethod': 'str',
        'CentralCoolingDesignSupplyAirHumidityRatio': 'float',
        'CentralCoolingDesignSupplyAirTemperature': 'float',
        'CentralHeatingDesignSupplyAirHumidityRatio': 'float',
        'CentralHeatingDesignSupplyAirTemperature': 'float',
        'CentralHeatingMaximumSystemAirFlowRatio': 'float',
        'CoolingDesignAirFlowMethod': 'str',
        'CoolingDesignAirFlowRate': 'float',
        'CoolingDesignCapacity': 'float',
        'CoolingDesignCapacityMethod': 'str',
        'CoolingDesignCapacityPerFloorArea': 'float',
        'CoolingFractionofAutosizedCoolingSupplyAirFlowRate': 'float',
        'CoolingSupplyAirFlowRatePerFloorArea': 'float',
        'CoolingSupplyAirFlowRatePerUnitCoolingCapacity': 'float',
        'DesignOutdoorAirFlowRate': 'float',
        'FractionofAutosizedCoolingDesignCapacity': 'float',
        'FractionofAutosizedHeatingDesignCapacity': 'float',
        'HeatingDesignAirFlowMethod': 'str',
        'HeatingDesignAirFlowRate': 'float',
        'HeatingDesignCapacity': 'float',
        'HeatingDesignCapacityMethod': 'str',
        'HeatingDesignCapacityPerFloorArea': 'float',
        'HeatingFractionofAutosizedCoolingSupplyAirFlowRate': 'float',
        'HeatingFractionofAutosizedHeatingSupplyAirFlowRate': 'float',
        'HeatingSupplyAirFlowRatePerFloorArea': 'float',
        'HeatingSupplyAirFlowRatePerUnitHeatingCapacity': 'float',
        'OccupantDiversity': 'float',
        'PrecoolDesignHumidityRatio': 'float',
        'PrecoolDesignTemperature': 'float',
        'PreheatDesignHumidityRatio': 'float',
        'PreheatDesignTemperature': 'float',
        'SizingOption': 'str',
        'SystemOutdoorAirMethod': 'str',
        'TypeofLoadtoSizeOn': 'str',
        'ZoneMaximumOutdoorAirFraction': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_SizingSystem'] = PydanticField(default='IB_SizingSystem')

__all__ = [
    'IB_SizingSystem',
]
