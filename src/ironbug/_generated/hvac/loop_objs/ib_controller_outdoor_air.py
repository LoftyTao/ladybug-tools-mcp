"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ControllerOutdoorAir(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ControllerOutdoorAir'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_ControllerOutdoorAir.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_ModelObject',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_ControllerOutdoorAir_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'MinimumOutdoorAirSchedule',
        'MinimumFractionofOutdoorAirSchedule',
        'MaximumFractionofOutdoorAirSchedule',
        'TimeofDayEconomizerControlSchedule',
        'MinimumOutdoorAirFlowRate',
        'MaximumOutdoorAirFlowRate',
        'EconomizerControlType',
        'EconomizerControlActionType',
        'EconomizerMaximumLimitDryBulbTemperature',
        'EconomizerMaximumLimitEnthalpy',
        'EconomizerMaximumLimitDewpointTemperature',
        'ElectronicEnthalpyLimitCurve',
        'EconomizerMinimumLimitDryBulbTemperature',
        'LockoutType',
        'MinimumLimitType',
        'HighHumidityControl',
        'HighHumidityOutdoorAirFlowRatio',
        'ControlHighIndoorHumidityBasedOnOutdoorHumidityRatio',
        'HeatRecoveryBypassControlType',
        'EconomizerOperationStaging',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'ControlHighIndoorHumidityBasedOnOutdoorHumidityRatio': 'bool | str',
        'EconomizerControlActionType': 'str',
        'EconomizerControlType': 'str',
        'EconomizerMaximumLimitDewpointTemperature': 'float',
        'EconomizerMaximumLimitDryBulbTemperature': 'float',
        'EconomizerMaximumLimitEnthalpy': 'float',
        'EconomizerMinimumLimitDryBulbTemperature': 'float',
        'EconomizerOperationStaging': 'str',
        'HeatRecoveryBypassControlType': 'str',
        'HighHumidityControl': 'bool | str',
        'HighHumidityOutdoorAirFlowRatio': 'float',
        'LockoutType': 'str',
        'MaximumOutdoorAirFlowRate': 'float',
        'MinimumLimitType': 'str',
        'MinimumOutdoorAirFlowRate': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'ElectronicEnthalpyLimitCurve': 'IB_Curve',
        'MaximumFractionofOutdoorAirSchedule': 'IB_Schedule',
        'MinimumFractionofOutdoorAirSchedule': 'IB_Schedule',
        'MinimumOutdoorAirSchedule': 'IB_Schedule',
        'TimeofDayEconomizerControlSchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ControllerOutdoorAir'] = PydanticField(default='IB_ControllerOutdoorAir')

__all__ = [
    'IB_ControllerOutdoorAir',
]
