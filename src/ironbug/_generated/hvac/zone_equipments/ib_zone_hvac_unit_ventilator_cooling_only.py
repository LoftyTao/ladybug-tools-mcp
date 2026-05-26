"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ZoneHVACUnitVentilator_CoolingOnly(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ZoneHVACUnitVentilator_CoolingOnly'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ZoneEquipments/ZoneHVAC/IB_ZoneHVACUnitVentilator_CoolingOnly.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ZoneEquipment',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = None
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'MaximumSupplyAirFlowRate',
        'OutdoorAirControlType',
        'MinimumOutdoorAirFlowRate',
        'MinimumOutdoorAirSchedule',
        'MaximumOutdoorAirFlowRate',
        'MaximumOutdoorAirFractionorTemperatureSchedule',
        'SupplyAirFanOperatingModeSchedule',
        'HeatingConvergenceTolerance',
        'CoolingConvergenceTolerance',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'CoolingConvergenceTolerance': 'float',
        'HeatingConvergenceTolerance': 'float',
        'MaximumOutdoorAirFlowRate': 'float',
        'MaximumSupplyAirFlowRate': 'float',
        'MinimumOutdoorAirFlowRate': 'float',
        'OutdoorAirControlType': 'str',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
        'MaximumOutdoorAirFractionorTemperatureSchedule': 'IB_Schedule',
        'MinimumOutdoorAirSchedule': 'IB_Schedule',
        'SupplyAirFanOperatingModeSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ZoneHVACUnitVentilator_CoolingOnly'] = PydanticField(default='IB_ZoneHVACUnitVentilator_CoolingOnly')

__all__ = [
    'IB_ZoneHVACUnitVentilator_CoolingOnly',
]
