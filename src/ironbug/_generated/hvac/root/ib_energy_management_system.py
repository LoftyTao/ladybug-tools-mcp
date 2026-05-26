"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_EnergyManagementSystem(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_EnergyManagementSystem'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/IB_EnergyManagementSystem.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = ()
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_SET: ClassVar[str | None] = None
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'Actuators',
        'Sensors',
        'ProgramClnManagers',
        'Variables',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = (
        'Actuators',
        'Sensors',
        'ProgramClnManagers',
        'Variables',
    )
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'Actuators': 'List<IB_EnergyManagementSystemActuator>',
        'ProgramClnManagers': 'List<IB_EnergyManagementSystemProgramCallingManager>',
        'Sensors': 'List<IB_EnergyManagementSystemSensor>',
        'Variables': 'List<BaseClass.IB_EnergyManagementSystemVariable>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {
        'Actuators': 'List<IB_EnergyManagementSystemActuator>',
        'ProgramClnManagers': 'List<IB_EnergyManagementSystemProgramCallingManager>',
        'Sensors': 'List<IB_EnergyManagementSystemSensor>',
        'Variables': 'List<BaseClass.IB_EnergyManagementSystemVariable>',
    }
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_EnergyManagementSystem'] = PydanticField(default='IB_EnergyManagementSystem')
    Actuators: list[IB_EnergyManagementSystemActuator] | None = PydanticField(default=None)
    Sensors: list[IB_EnergyManagementSystemSensor] | None = PydanticField(default=None)
    ProgramClnManagers: list[IB_EnergyManagementSystemProgramCallingManager] | None = PydanticField(default=None)
    Variables: Any = PydanticField(default=None)

__all__ = [
    'IB_EnergyManagementSystem',
]
