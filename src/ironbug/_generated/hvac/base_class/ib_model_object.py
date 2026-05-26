"""Generated Ironbug HVAC source mirror. Do not edit by hand."""

from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import ConfigDict, Field as PydanticField

from ironbug.hvac._base import IronbugInterfaceMarker, IronbugSourceMixin
from ironbug.hvac.base_class import IB_ModelObject as IronbugModelObjectBase


class IB_ModelObject(IronbugSourceMixin, IronbugModelObjectBase):
    SOURCE_CLASS: ClassVar[str] = 'IB_ModelObject'
    SOURCE_PATH: ClassVar[str] = 'src/Ironbug.HVAC/BaseClass/IB_ModelObject.cs'
    SOURCE_NAMESPACE: ClassVar[str] = 'Ironbug.HVAC.BaseClass'
    SOURCE_BASES: ClassVar[tuple[str, ...]] = ()
    SOURCE_INTERFACES: ClassVar[tuple[str, ...]] = (
        'IIB_ModelObject',
    )
    SOURCE_FIELD_SET: ClassVar[str | None] = None
    SOURCE_PROPERTIES: ClassVar[tuple[str, ...]] = (
        'Memo',
        'SimulationOutputVariables',
        'EmsActuators',
        'EmsInternalVariables',
        'IPUnit',
        'Children',
        'CustomAttributes',
        'IBProperties',
        'CustomOutputVariables',
        'CustomSensors',
        'CustomInternalVariables',
        'CustomActuators',
    )
    SOURCE_DATA_MEMBERS: ClassVar[tuple[str, ...]] = (
        'Children',
        'CustomAttributes',
        'IBProperties',
        'CustomOutputVariables',
        'CustomSensors',
        'CustomInternalVariables',
        'CustomActuators',
    )
    SOURCE_SHOULD_SERIALIZE: ClassVar[tuple[str, ...]] = (
        'Children',
        'CustomAttributes',
        'CustomOutputVariables',
        'CustomSensors',
        'CustomInternalVariables',
        'CustomActuators',
        'IBProperties',
    )
    SOURCE_FIELD_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_FIELD_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_TYPES: ClassVar[dict[str, str]] = {}
    SOURCE_FIELD_TARGET_LIST_NAMES: ClassVar[tuple[str, ...]] = ()
    SOURCE_METADATA_ONLY_FIELDS: ClassVar[tuple[str, ...]] = ()
    SOURCE_PROPERTY_TYPES: ClassVar[dict[str, str]] = {
        'Children': 'IB_Children',
        'CustomActuators': 'List<IB_EnergyManagementSystemActuator>',
        'CustomAttributes': 'IB_FieldArgumentSet',
        'CustomInternalVariables': 'List<IB_EnergyManagementSystemInternalVariable>',
        'CustomOutputVariables': 'List<IB_OutputVariable>',
        'CustomSensors': 'List<IB_EnergyManagementSystemSensor>',
        'EmsActuators': 'Dictionary<string, string>',
        'EmsInternalVariables': 'IEnumerable<string>',
        'IBProperties': 'IB_PropArgumentSet',
        'IPUnit': 'bool',
        'Memo': 'string',
        'SimulationOutputVariables': 'IEnumerable<string>',
    }
    SOURCE_DATA_MEMBER_TYPES: ClassVar[dict[str, str]] = {
        'Children': 'IB_Children',
        'CustomActuators': 'List<IB_EnergyManagementSystemActuator>',
        'CustomAttributes': 'IB_FieldArgumentSet',
        'CustomInternalVariables': 'List<IB_EnergyManagementSystemInternalVariable>',
        'CustomOutputVariables': 'List<IB_OutputVariable>',
        'CustomSensors': 'List<IB_EnergyManagementSystemSensor>',
        'IBProperties': 'IB_PropArgumentSet',
    }
    ENERGYPLUS_OBJECT: ClassVar[str | None] = None
    OPENSTUDIO_CLASS: ClassVar[str | None] = None
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True, extra='allow')
    type: Literal['IB_ModelObject'] = PydanticField(default='IB_ModelObject')
    Memo: str | None = PydanticField(default=None)
    SimulationOutputVariables: Any = PydanticField(default=None)
    EmsActuators: Any = PydanticField(default=None)
    EmsInternalVariables: Any = PydanticField(default=None)
    IPUnit: bool | None = PydanticField(default=None)
    CustomOutputVariables: list[IB_OutputVariable] | None = PydanticField(default=None)
    CustomSensors: list[IB_EnergyManagementSystemSensor] | None = PydanticField(default=None)
    CustomInternalVariables: list[IB_EnergyManagementSystemInternalVariable] | None = PydanticField(default=None)
    CustomActuators: list[IB_EnergyManagementSystemActuator] | None = PydanticField(default=None)

__all__ = [
    'IB_ModelObject',
]
