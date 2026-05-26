"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ThermalZone(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ThermalZone'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_ThermalZone.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.BaseClass'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_HVACObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_AirLoopObject',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ThermalZone_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'AirTerminal',
        'ZoneEquipments',
        'SupplyPlenum',
        'ReturnPlenum',
        'AllowMultiAirLoops',
        'IsAirTerminalBeforeZoneEquipments',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = (
        'AirTerminal',
        'ZoneEquipments',
        'SizingZone',
        'SupplyPlenum',
        'ReturnPlenum',
    )
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = (
        'AirTerminal',
        'ZoneEquipments',
        'IB_SizingZone',
        'SupplyPlenum',
        'ReturnPlenum',
    )
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'Multiplier',
        'CeilingHeight',
        'Volume',
        'ZoneInsideConvectionAlgorithm',
        'ZoneOutsideConvectionAlgorithm',
        'ZoneConditioningEquipmentListName',
        'ThermostatSetpointDualSetpoint',
        'ZoneControlHumidistat',
        'ZoneControlContaminantController',
        'FractionofZoneControlledbyPrimaryDaylightingControl',
        'FractionofZoneControlledbySecondaryDaylightingControl',
        'DaylightingControlsAvailabilitySchedule',
        'RenderingColor',
        'UseIdealAirLoads',
        'LoadDistributionScheme',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CeilingHeight': 'float',
        'FractionofZoneControlledbyPrimaryDaylightingControl': 'float',
        'FractionofZoneControlledbySecondaryDaylightingControl': 'float',
        'LoadDistributionScheme': 'str | float | int | bool',
        'Multiplier': 'int',
        'RenderingColor': 'str | float | int | bool',
        'ThermostatSetpointDualSetpoint': 'str | float | int | bool',
        'UseIdealAirLoads': 'bool | str',
        'Volume': 'float',
        'ZoneConditioningEquipmentListName': 'str',
        'ZoneControlContaminantController': 'str | float | int | bool',
        'ZoneControlHumidistat': 'str | float | int | bool',
        'ZoneInsideConvectionAlgorithm': 'str',
        'ZoneOutsideConvectionAlgorithm': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'DaylightingControlsAvailabilitySchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'AirTerminal': 'IB_AirTerminal',
        'AllowMultiAirLoops': 'bool',
        'IsAirTerminalBeforeZoneEquipments': 'bool',
        'ReturnPlenum': 'IB_ThermalZone',
        'SupplyPlenum': 'IB_ThermalZone',
        'ZoneEquipments': 'List<IIB_ZoneEquipment>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {
        'AirTerminal': 'IB_AirTerminal',
        'ReturnPlenum': 'IB_ThermalZone',
        'SizingZone': 'IB_SizingZone',
        'SupplyPlenum': 'IB_ThermalZone',
        'ZoneEquipments': 'List<IIB_ZoneEquipment>',
    }
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ThermalZone'] = PydanticField(default='IB_ThermalZone')
    AirTerminal: Any = PydanticField(default=None)
    ZoneEquipments: Any = PydanticField(default=None)
    SupplyPlenum: IB_ThermalZone | None = PydanticField(default=None)
    ReturnPlenum: IB_ThermalZone | None = PydanticField(default=None)
    AllowMultiAirLoops: bool | None = PydanticField(default=None)
    IsAirTerminalBeforeZoneEquipments: bool | None = PydanticField(default=None)
    SizingZone: IB_SizingZone | None = PydanticField(default=None)

__all__ = [
    'IB_ThermalZone',
]
