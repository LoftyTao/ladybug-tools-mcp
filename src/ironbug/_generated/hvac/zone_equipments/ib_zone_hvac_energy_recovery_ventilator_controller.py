"""Incremental Ironbug HVAC source mirror."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ZoneHVACEnergyRecoveryVentilatorController(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ZoneHVACEnergyRecoveryVentilatorController'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/ZoneEquipments/ZoneHVAC/IB_ZoneHVACEnergyRecoveryVentilatorController.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ModelObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ZoneHVACEnergyRecoveryVentilatorController_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'TemperatureHighLimit',
        'TemperatureLowLimit',
        'EnthalpyHighLimit',
        'DewpointTemperatureLimit',
        'ElectronicEnthalpyLimitCurve',
        'ExhaustAirTemperatureLimit',
        'ExhaustAirEnthalpyLimit',
        'TimeofDayEconomizerFlowControlSchedule',
        'HighHumidityControlFlag',
        'HighHumidityOutdoorAirFlowRatio',
        'ControlHighIndoorHumidityBasedonOutdoorHumidityRatio',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ControlHighIndoorHumidityBasedonOutdoorHumidityRatio': 'bool | str',
        'DewpointTemperatureLimit': 'float',
        'EnthalpyHighLimit': 'float',
        'ExhaustAirEnthalpyLimit': 'str',
        'ExhaustAirTemperatureLimit': 'str',
        'HighHumidityControlFlag': 'bool | str',
        'HighHumidityOutdoorAirFlowRatio': 'float',
        'TemperatureHighLimit': 'float',
        'TemperatureLowLimit': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'ElectronicEnthalpyLimitCurve': 'IB_Curve',
        'TimeofDayEconomizerFlowControlSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ZoneHVACEnergyRecoveryVentilatorController'] = PydanticField(default='IB_ZoneHVACEnergyRecoveryVentilatorController')

__all__ = [
    'IB_ZoneHVACEnergyRecoveryVentilatorController',
]
