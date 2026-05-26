"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_FanVariableVolume(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_FanVariableVolume'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/LoopObjs/IB_FanVariableVolume.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = (
        'IB_Fan',
    )
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = 'IB_FanVariableVolume_FieldSet'
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = ()
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = ()
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = (
        'AvailabilitySchedule',
        'FanTotalEfficiency',
        'FanEfficiency',
        'PressureRise',
        'MaximumFlowRate',
        'FanPowerMinimumFlowRateInputMethod',
        'FanPowerMinimumFlowFraction',
        'FanPowerMinimumAirFlowRate',
        'MotorEfficiency',
        'MotorInAirstreamFraction',
        'FanPowerCoefficient1',
        'FanPowerCoefficient2',
        'FanPowerCoefficient3',
        'FanPowerCoefficient4',
        'FanPowerCoefficient5',
        'EndUseSubcategory',
    )
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {
        'EndUseSubcategory': 'str',
        'FanEfficiency': 'str | float | int | bool',
        'FanPowerCoefficient1': 'float',
        'FanPowerCoefficient2': 'float',
        'FanPowerCoefficient3': 'float',
        'FanPowerCoefficient4': 'float',
        'FanPowerCoefficient5': 'float',
        'FanPowerMinimumAirFlowRate': 'float',
        'FanPowerMinimumFlowFraction': 'float',
        'FanPowerMinimumFlowRateInputMethod': 'str',
        'FanTotalEfficiency': 'float',
        'MaximumFlowRate': 'float',
        'MotorEfficiency': 'float',
        'MotorInAirstreamFraction': 'float',
        'PressureRise': 'float',
    }
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {
        'AvailabilitySchedule': 'IB_Schedule',
    }
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {}
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_FanVariableVolume'] = PydanticField(default='IB_FanVariableVolume')

__all__ = [
    'IB_FanVariableVolume',
]
